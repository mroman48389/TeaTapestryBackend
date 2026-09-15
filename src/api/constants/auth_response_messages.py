from dataclasses import dataclass
#from .messages_common import CommonMessages

@dataclass(frozen = True)
class AuthResponseMessages: #pragma: no cover
    #FAILED_TO_CREATE_VERIFICATION_TOKEN = CommonMessages.FAILED_TO_CREATE_VERIFICATION_TOKEN
    EMAIL_ALREADY_EXISTS: str = "A user with this email address already exists."
    ERROR_CREATING_ACCOUNT: str = "An unexpected error occurred while creating the account."
    ERROR_REFRESH_ACCOUNT: str = "An unexpected error occurred while refreshing the new account."
    FAILED_TO_CREATE_VERIF_TOKEN: str = "Failed to create verification token."
    EMAIL_ALREADY_VERIF: str = "Email is already verified."
    ERROR_PREP_VERIF_TOKEN: str = (
        "An unexpected error occurred while preparing the verification token."
    )
    VERIF_EMAIL_SENT: str = "Verification email sent."
    INVALID_UNKNOWN_VERIF_TOKEN: str = "Invalid or unknown verification token."
    VERIF_LINK_ALREADY_USED: str = "This verification link has already been used."
    VERIF_LINK_EXPIRED: str = "This verification link has expired."
    USER_NO_LONGER_EXISTS: str = "User no longer exists."
    FAILED_TO_DELETE_USER_DATA: str = "Failed to delete user data."
    PASSWORD_CONFIRM_REQ: str = "Password confirmation required."
    FAILED_TO_DELETE_ACCOUNT: str = "Failed to delete user account."
    INVALID_PASSWORD: str = "Invalid password."
    FAILED_TO_CONFIRM_PASSWORD: str = "Failed to confirm password."
    ERROR_RESETTING_PASSWORD: str = "An unexpected error occurred while resetting the password."
    INVALID_EMAIL_PASSWORD: str = "Invalid email or password."
    CANT_CREATE_SESSION_TOKEN: str = "Could not create session token."
    COULD_NOT_REVOKE_SESSION: str = "Could not revoke session token."
    ERROR_VERIFYING_EMAIL: str = "An unexpected error occurred while verifying the email."
    COULD_NOT_REVOKE_ALL_SESSIONS: str = "Could not revoke all session tokens."
    SESSION_NOT_FOUND: str = "Session not found."
    SESSION_ALREADY_TERMINATED: str = "Session already terminated."
    FAILED_TERMINATE_SESSION: str = "Failed to terminate session."
    MISSING_REFRESH_TOKEN: str = "Missing refresh token."
    INVALID_REFRESH_TOKEN: str = "Invalid refresh token."
    REFRESH_TOKEN_EXPIRED: str = "Refresh token expired."
    REFRESH_TOKEN_EXPIRED_STALE: str = "Refresh token expired or stale."
    REUSE_DETECTED_SESSIONS_REVOKED: str = "Refresh token reuse detected. All sessions revoked."
    FAILED_EXPORT_USER_DATA: str = "Failed to export user data."

    LOGGED_OUT_ALL_DEVICES: str = "Logged out of all devices."
    EMAIL_VERIFIED: str = "Email verified successfully."
    RESET_LINK_SENT: str = "If the email exists, a reset link has been sent."
    SESSION_TERMINATED_SUCCESS: str = "Session terminated successfully."
