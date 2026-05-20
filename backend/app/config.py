from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sourcer.db"
    frontend_origin: str = "http://localhost:5173"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}"
    stripe_cancel_url: str = "http://localhost:5173/payment/cancel"
    stripe_platform_fee_bps: int = 300
    stripe_supplier_1_account_id: str = "acct_1SourcerZambalesTest"
    stripe_supplier_2_account_id: str = "acct_1SourcerOlongapoTest"
    stripe_supplier_3_account_id: str = "acct_1SourcerSubicTest"
    stripe_supplier_4_account_id: str = "acct_1SourcerBataanTest"
    stripe_supplier_5_account_id: str = "acct_1SourcerIbaTest"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
