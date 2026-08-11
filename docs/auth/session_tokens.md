# Session Tokens

>    Before the backend has session tokens, endpoints used stateless refresh tokens that 
>    did not persist on the server. While that system was simpler, making them stateful 
>    gives us many important advantages: 
>
>    1. The ability to log the user out of one or all devices. If the user is
>       logged in on their computer and phone, for example, and their phone is compromised, we
>       can log them out of their phone and computer. 
>
>    2. An easy way to delete the user's account.
>           
>    3. The ability to export user data, including active sessions, login history, and tokens.
>
>    4. The ability to easily log out of all devices if the user resets their password.
>
>    5. A viewable history of users' sessions.
>

> Sessions tokens are opaque refresh tokens. Opaque means they are random strings with no 
> internal structure that can only be validated by looking them up in the database. They should
> be opaque because they:
>
>    1. are long-lived
>    2. must be revocable
>    3. must be trackable
>    4. must be tied to devices
>    5. must be deletable
>    6. must support logout-everywhere
>    7. must support password-reset invalidation
>    8. must not leak user info if stolen
>
> By contrast, our JWT access tokens are non-opaque. They should be because they
>
>    1. are short-lived
>    2. don't need revocation
>    3. can be used by the frontend to check auth state 
>    4. must be validated quickly without shared state
>    5. can be validated cryptographically by any backend service.