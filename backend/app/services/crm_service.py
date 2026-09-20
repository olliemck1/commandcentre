import json
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..models.crm import Person, Interaction
from ..models.journal import JournalEntry
from ..schemas.journal import ExtractedPerson
from ..schemas.crm import PersonUpdate

logger = logging.getLogger("crm_service")

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)

class CRMService:
    def process_extracted_people(
        self,
        db: Session,
        people: List[ExtractedPerson],
        journal_entry: JournalEntry,
        date_str: str
    ) -> List[Interaction]:
        created_interactions = []

        for p_data in people:
            raw_name = p_data.name.strip()
            # Clean leading conjunctions/prepositions
            for prefix in ("and ", "with ", "to ", "from ", "the "):
                if raw_name.lower().startswith(prefix):
                    raw_name = raw_name[len(prefix):].strip()

            if not raw_name or len(raw_name) < 2:
                continue

            target_slug = slugify(raw_name)

            # Look up person by slug, exact name, or alias
            person = db.query(Person).filter(
                or_(
                    Person.slug == target_slug,
                    func.lower(Person.name) == raw_name.lower()
                )
            ).first()

            if not person:
                # Check aliases or first-name matching
                all_people = db.query(Person).all()
                for candidate in all_people:
                    aliases = json.loads(candidate.aliases or "[]")
                    # Check exact alias match
                    if any(a.lower() == raw_name.lower() for a in aliases):
                        person = candidate
                        break
                    # Check first name match if raw_name is a single name
                    candidate_first = candidate.name.split()[0].lower()
                    if raw_name.lower() == candidate_first or candidate.slug == target_slug:
                        person = candidate
                        break
                    # Check if candidate name is prefix of raw_name or vice versa
                    if candidate.name.lower().startswith(raw_name.lower() + " ") or raw_name.lower().startswith(candidate.name.lower() + " "):
                        person = candidate
                        break

            # If still not found, create new Person
            if not person:
                initial_notes = ""
                if p_data.facts_learned:
                    initial_notes = "\n".join([f"• {f}" for f in p_data.facts_learned])
                
                initial_tags = ["contact"]
                if p_data.location:
                    initial_tags.append("social")

                person = Person(
                    name=raw_name,
                    slug=target_slug,
                    aliases=json.dumps([raw_name]),
                    first_met_date=date_str,
                    last_seen_date=date_str,
                    interaction_count=1,
                    notes_summary=initial_notes,
                    tags=json.dumps(initial_tags),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(person)
                db.flush() # get person.id
            else:
                # Update existing person
                person.interaction_count += 1
                if not person.last_seen_date or date_str >= person.last_seen_date:
                    person.last_seen_date = date_str
                
                # Append newly learned facts if not already present
                existing_notes = person.notes_summary or ""
                new_facts = []
                for f in p_data.facts_learned:
                    if f.lower() not in existing_notes.lower():
                        new_facts.append(f)
                
                if new_facts:
                    facts_bullet = "\n".join([f"• {f}" for f in new_facts])
                    person.notes_summary = (existing_notes + "\n" + facts_bullet).strip()

                # Add alias if it's slightly different
                aliases = json.loads(person.aliases or "[]")
                if raw_name not in aliases:
                    aliases.append(raw_name)
                    person.aliases = json.dumps(aliases)

                person.updated_at = datetime.utcnow()

            # Create Interaction
            interaction = Interaction(
                person_id=person.id,
                journal_entry_id=journal_entry.id,
                date=date_str,
                context_snippet=p_data.context or journal_entry.raw_text[:200],
                sentiment=p_data.sentiment or "neutral",
                location=p_data.location,
                extracted_facts=json.dumps(p_data.facts_learned or []),
                created_at=datetime.utcnow()
            )
            db.add(interaction)
            created_interactions.append(interaction)

        db.commit()
        return created_interactions

    def get_people(
        self,
        db: Session,
        search: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(Person)
        if search:
            s = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Person.name).like(s),
                    func.lower(Person.notes_summary).like(s),
                    func.lower(Person.aliases).like(s)
                )
            )
        
        people = query.order_by(Person.last_seen_date.desc().nullslast()).all()
        result = []
        for p in people:
            d = p.to_dict(include_interactions=False)
            if tag:
                if tag.lower() not in [t.lower() for t in d.get("tags", [])]:
                    continue
            result.append(d)
        return result

    def get_person_detail(self, db: Session, person_id: int) -> Optional[Dict[str, Any]]:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            return None
        return person.to_dict(include_interactions=True)

    def update_person(self, db: Session, person_id: int, update_data: PersonUpdate) -> Optional[Dict[str, Any]]:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            return None

        if update_data.name is not None:
            person.name = update_data.name
            person.slug = slugify(update_data.name)
        if update_data.aliases is not None:
            person.aliases = json.dumps(update_data.aliases)
        if update_data.first_met_date is not None:
            person.first_met_date = update_data.first_met_date
        if update_data.notes_summary is not None:
            person.notes_summary = update_data.notes_summary
        if update_data.tags is not None:
            person.tags = json.dumps(update_data.tags)

        person.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(person)
        return person.to_dict(include_interactions=True)

    def delete_person(self, db: Session, person_id: int) -> bool:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            return False
        db.delete(person)
        db.commit()
        return True

crm_service = CRMService()
