import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.journal import JournalEntry
from app.models.crm import Person, Interaction
from app.schemas.journal import ExtractedPerson
from app.services.crm_service import crm_service

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_process_extracted_people_creates_new_person(db_session):
    journal = JournalEntry(date="2026-09-20", raw_text="Met Sarah Miller for coffee.")
    db_session.add(journal)
    db_session.flush()

    people_data = [
        ExtractedPerson(
            name="Sarah Miller",
            context="Coffee in Covent Garden",
            sentiment="positive",
            facts_learned=["Likes decaf after 2pm", "Promoted to Director"],
            location="Covent Garden"
        )
    ]

    interactions = crm_service.process_extracted_people(
        db=db_session,
        people=people_data,
        journal_entry=journal,
        date_str="2026-09-20"
    )

    assert len(interactions) == 1
    person = db_session.query(Person).filter(Person.slug == "sarah-miller").first()
    assert person is not None
    assert person.name == "Sarah Miller"
    assert person.interaction_count == 1
    assert "Director" in person.notes_summary
    assert "Covent Garden" in interactions[0].location

def test_process_extracted_people_updates_existing_person(db_session):
    journal1 = JournalEntry(date="2026-09-18", raw_text="First meeting with Alex Chen.")
    db_session.add(journal1)
    db_session.flush()

    crm_service.process_extracted_people(
        db=db_session,
        people=[ExtractedPerson(name="Alex Chen", context="Intro", facts_learned=["Plays tennis"])],
        journal_entry=journal1,
        date_str="2026-09-18"
    )

    journal2 = JournalEntry(date="2026-09-20", raw_text="Second meeting with Alex.")
    db_session.add(journal2)
    db_session.flush()

    crm_service.process_extracted_people(
        db=db_session,
        people=[ExtractedPerson(name="Alex", context="Follow up", facts_learned=["Training for marathon"])],
        journal_entry=journal2,
        date_str="2026-09-20"
    )

    alex = db_session.query(Person).filter(Person.name == "Alex Chen").first()
    assert alex is not None
    assert alex.interaction_count == 2
    assert alex.last_seen_date == "2026-09-20"
    assert "marathon" in alex.notes_summary
    assert "tennis" in alex.notes_summary
