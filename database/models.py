from sqlalchemy import String, Float, BigInteger, func, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression
from datetime import datetime
import pytz

ekb_tz = pytz.timezone("Asia/Yekaterinburg")

class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nick: Mapped[str] = mapped_column(String(30))
    tg_id: Mapped[int] = mapped_column(BigInteger)
    phone_number: Mapped[str] = mapped_column(String(12))
    created: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ekb_tz)
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    qr_code : Mapped[str] = mapped_column(default='')


class Category(Base):
    __tablename__ = 'category'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Product(Base):
    __tablename__ = 'product'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(100), nullable=False)
    description : Mapped[str] =  mapped_column(String(1000))
    price : Mapped[float] = mapped_column(Float(asdecimal=True), nullable=False)
    count : Mapped[int]  =mapped_column(default=0)
    image : Mapped[str] = mapped_column(default='')
    created : Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id', ondelete='CASCADE'), nullable=False)
    category: Mapped['Category'] = relationship(backref='product')

class Cart(Base):
    __tablename__ = 'cart'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.tg_id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    quantity: Mapped[int]

    user: Mapped['Users'] = relationship(backref='cart')
    product: Mapped['Product'] = relationship(backref='cart')