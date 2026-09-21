# Action First

Agent responses that start with the result or the next action.

## Install

Ask your agent:

```text
Install the Action First skill from https://github.com/brissonjo-sudo/action-first.
Review the files before installing and explain where it will be installed.
```

Or copy `skills/action-first/` into your agent's skill directory. Invoke
`$action-first` in Codex or `/action-first` in Claude Code. Installation does not
activate the mode by itself.

## What changes

**Before**

> Good question. There are several moving pieces in the authentication flow. You may
> want to inspect the function, then review the tests and possibly the dependencies.

**After**

> Open `src/auth.ts:42` and inspect the `verifyToken` call.
>
> 1. Fix the call.
> 2. Run `npm test -- auth.spec.ts`.
> 3. If it fails, capture the first error.

Action First is an explicit output preference. It requires and infers no diagnosis.
It sends no data and installs no network service.

## Verify

Ask the agent to use Action First and explain how to initialize an empty Git repository.
The response should lead with the command or first action, preserve every required step,
and omit generic closing filler.

MIT licensed. See [LICENSE](LICENSE).
