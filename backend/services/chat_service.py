from sqlalchemy.orm import Session

from models import Conversation, Message


def create_conversation(
    db: Session,
    company_id: int
):
    conversation = Conversation(
        company_id=company_id
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str
):
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def get_conversation_messages(
    db: Session,
    conversation_id: int
):
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(
        Message.created_at.asc()
    ).all()