import resend

from src.core.env import IS_RUNNING_TESTS
from src.utils.log_utils import safe_debug, safe_exception
from src.utils.auth.token_utils import build_frontend_token_link
from src.core.config import settings
from src.db.models.auth.user_models import UserInternalModel
from src.constants.token_constants import VERIF_TOKEN_EXPIR_MIN

resend.api_key = settings.resend_api_key


def generate_html(
    subject: str, 
    username: str, 
    main_msg: str, 
    link: str, 
    link_text: str, 
    disregard_msg: str
) -> str:
    html = f"""
        <div 
            style = "
                max-width: 600px;
                margin: auto;
                font-family: Calibri, sans-serif;
                padding: 24px;
            "
        >
            <h1 
                style = "
                    color: #3e241d;
                    text-align: center;
                    font-size: 36px;
                "
            >
                Tea Tapestry
            </h1>

            <h2 style = "margin-block: 40px; font-size: 30px">
                {subject}
            </h2>

            <p style = "font-size: 18px">
                Hello {username},
            </p>

            <p style = "font-size: 18px">
                {main_msg} 
            </p>

            <div 
                style = "
                    margin: 40px 0px; 
                    text-align: center;
                "
            >
                <a
                    href = "{link}"
                    style = "
                        background-color: #3e241d;
                        color: white;
                        text-decoration: none;
                        border-radius: 6px;
                        padding: 12px 80px;
                        display: inline-block;
                        font-size: 18px;
                    "
                >
                    {link_text}
                </a>
            </div>

            <p style = "font-size: 18px">
                This link will expire in {VERIF_TOKEN_EXPIR_MIN} minutes.
            </p>

            <p style = "font-size: 18px">
                {disregard_msg}
            </p>

            <p style = "margin-top: 40px; font-size: 18px">
                -The Tea Tapestry Team
            </p>
        </div>
    """

    return html


def send_verification_email(user: UserInternalModel, raw_token: str):
    verification_link = build_frontend_token_link("verify-email", raw_token)

    safe_debug(f"Send email to {user.email}: {verification_link}")

    html = generate_html(
        subject = "Verify your email address",
        username = user.display_name,
        main_msg = (
            "Thank you for signing up for a Tea Tapestry account! Click the button below to "
            "verify your email address." 
        ),
        link = verification_link,
        link_text = "Verify Email",
        disregard_msg = "If you did not sign up for a Tea Tapestry account, please disregard this email."
    )

    if not IS_RUNNING_TESTS:
        send_email(
            to_email = user.email,
            subject = "Verify Your Tea Tapestry Account",
            html = html,
        )


def send_password_reset_email(user: UserInternalModel, raw_token: str):
    password_reset_link = build_frontend_token_link("reset-password", raw_token)

    safe_debug(f"Send password reset email to {user.email}: {password_reset_link}")

    html = generate_html(
        subject = "Password reset",
        username = user.display_name,
        main_msg = (
            "We received a request to reset your password. Click the button below to "
            "confirm."
        ),
        link = password_reset_link,
        link_text = "Reset Password",
        disregard_msg = "If you did not request a password reset, please disregard this email."
    )

    if not IS_RUNNING_TESTS:
        send_email(
            to_email = user.email,
            subject = "Reset Your Tea Tapestry Password",
            html = html,
        )


def send_email(to_email: str, subject: str, html: str):
    try:
        # We can only change "from": "onboarding@resend.dev" because we now have the
        # teatapestry.com domain. 
        response = resend.Emails.send(
            {
                "from": "Tea Tapestry <noreply@notifications.teatapestry.com>",
                "to": [to_email],
                "subject": subject,
                "html": html,
            }
        )

        # Write out the success response.
        safe_debug(f"Resend response: {response}")

        return response

    except Exception as exc:
        # Write the exception out so we can see what went wrong, then
        # bubble it back up so the endpoint handles it.
        safe_exception(f"Resend send failed: {exc}")
        raise


# if __name__ == "__main__":
#     html = generate_html(
#         subject = "Password reset",
#         username = "Me",
#         main_msg = (
#             "We received a request to reset your password. Click the button below to "
#             "confirm."
#         ),
#         link = "fake",
#         link_text = "Reset Password",
#         disregard_msg = "If you did not request a password reset, please disregard this email."
#     )

#     send_email(
#         to_email = "X@gmail.com",
#         subject = "Reset Your Tea Tapestry Password",
#         html = html,
#     )