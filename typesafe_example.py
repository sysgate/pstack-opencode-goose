#!/usr/bin/env python3
"""Minimal TypeSafe System One call with the API key read from macOS Keychain.

One-time setup (prompts for the key, so it never lands in shell history):
    security add-generic-password -a "$USER" -s typesafe -w

Install the SDK into the interpreter you run this with:
    python3 -m pip install typesafe-sdk

Run:
    python3 typesafe_example.py
"""

import os
import subprocess
import sys

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

KEYCHAIN_SERVICE = "typesafe"
# Below this real_ticket probability, ignore the other answers. Untuned; check on real data.
REAL_TICKET_MIN = 0.5
ON_TOPIC_MIN = 0.5


def load_api_key() -> None:
    """Ensure TYPESAFE_API_KEY is set, reading Keychain if the env var is absent."""
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    try:
        key = subprocess.check_output(
            [
                "security",
                "find-generic-password",
                "-a",
                os.environ.get("USER", ""),
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        key = ""
    if not key:
        sys.exit(
            f"No TYPESAFE_API_KEY in the environment or Keychain service "
            f"'{KEYCHAIN_SERVICE}'. Add it with:\n"
            f'  security add-generic-password -a "$USER" -s {KEYCHAIN_SERVICE} -w'
        )
    os.environ["TYPESAFE_API_KEY"] = key


TICKETS = [
    "I was charged twice. Please fix this ASAP.",
    "Hi! Just wondering whether you support exporting data to CSV. No rush at all.",
    "Your service has been down for three hours and we're losing customers. This is unacceptable!!",
    "Could you send me last month's invoice when you get a chance? Thanks.",
    "Not sure if this is the right place, but the app feels kind of slow lately?",
    "asdf qwerty 12345",
    # Borderline cases for the real_ticket gate:
    "thanks",
    "?",
    "Hello",
    "URGENT: You won a free cruise! Click http://bit.ly/x9 to claim your prize now.",
    "What's the capital of France?",
    "Wow, great job again. Third outage this week. Really impressive.",
    "Ich wurde zweimal belastet, bitte erstatten Sie mir das Geld.",
    "my password reset email never came, tried 3 times, jus need in today",
    # Realistic messy tickets:
    "Hey team, two things. 1) the dashboard export keeps timing out on big date ranges "
    "and 2) can you also tell me if we're still on the old pricing? Renewal is next month "
    "so no huge rush but would be good to know. Thx, Dana",
    "WHY IS MY ACCOUNT LOCKED?!?! I HAVE A PRESENTATION IN 20 MINUTES AND I CAN'T LOG IN "
    "😡😡 FIX IT NOW",
    "Hi, I've been a customer for 6 years and honestly the last few months have been rough: "
    "slow load times, two billing mistakes, and support took 9 days to reply last time. "
    "If this doesn't improve I'll have to look at alternatives.",
    "Getting this in the logs: TypeError: Cannot read properties of undefined (reading "
    "'id') at syncWorker.js:212 -- started after yesterday's update. any ideas?",
    "-----Original Message-----\nFrom: Priya\nSent: Tue\nSubject: RE: RE: FW: invoice\n\n"
    "see below, can someone on your end sort this out? \n\n> > we were double billed for "
    "March again\n\nSent from my iPhone",
    "it would be really nice if you guys added dark mode someday. not urgent at all just a "
    "thought :)",
    "I think someone else logged into my account. I got an email about a login from Russia "
    "at 3am and I didn't do that. Also my saved card was used for something I didn't buy.",
    "Interested in an enterprise plan for ~500 seats. Who do I talk to about pricing and SSO?",
    "still waiting on the refund from ticket #48213?? it's been 3 weeks",
    "Please unsubscribe me from all emails. Thank you.",
]

QUESTIONS = {
    "real_ticket": Noul(
        instructions="Is this a coherent message from a customer that asks for help, "
        "information, or action, or reports a problem, complaint, or feedback "
        "(even sarcastically or tersely), as opposed to gibberish, spam, a bare "
        "greeting or thanks, or an empty message?"
    ),
    "on_topic": Noul(
        instructions="Is this message about a company's product or service, such as "
        "an account, billing, an outage, or a bug (as opposed to a general-knowledge "
        "question or chit-chat unrelated to any product)?"
    ),
    "category": Choice(
        instructions="What is the main thing this ticket needs from us? If it mixes "
        "several, choose the one that most needs action.",
        criteria={
            "billing": "charges, invoices, refunds, pricing on an existing account",
            "bug": "something is broken, erroring, slow, or behaving incorrectly",
            "security": "suspected unauthorized access, fraud, or a data/security concern",
            "sales": "buying, plans, seat counts, quotes, or new-customer questions",
            "feature_request": "a suggestion or wish for new functionality",
            "account_access": "login, lockout, password, or account settings/admin",
            "other": "none of the above fits",
        },
    ),
    "churn_risk": Noul(
        instructions="Does the customer signal they may stop using the product, cancel, "
        "or switch to a competitor?"
    ),
    "security_concern": Noul(
        instructions="Does the message suggest possible unauthorized access to an "
        "account, fraud, or exposure of private data?"
    ),
    "billing": Noul(instructions="Is this ticket about billing?"),
    "tone": Choice(
        instructions="What is the customer's tone?",
        criteria={"calm": None, "frustrated": None, "angry": None},
    ),
    "urgency": Score(
        instructions="How urgent is this ticket?",
        criteria=["can wait", "this week", "today"],
    ),
}


def main() -> None:
    load_api_key()

    with TypeSafeClient() as client:
        for text in TICKETS:
            response = client.system_one(
                state={"document": text},
                questions=QUESTIONS,
            )
            tone = response.choices["tone"]
            urgency = response.scores["urgency"]
            real = response.nouls["real_ticket"].noul
            on_topic = response.nouls["on_topic"].noul
            one_line = " ".join(text.split())
            print(f"\n> {one_line[:80]}{'…' if len(one_line) > 80 else ''}")
            print(f"  real:    {real:.2f}  on_topic: {on_topic:.2f}")
            if real < REAL_TICKET_MIN or on_topic < ON_TOPIC_MIN:
                # Fail closed: the other answers were computed but are not trusted.
                why = "real" if real < REAL_TICKET_MIN else "on_topic"
                print(f"  SKIPPED ({why} below threshold) -> route to human review")
                continue
            cat = response.choices["category"]
            top2 = sorted(cat.probabilities.items(), key=lambda kv: -kv[1])[:2]
            print(f"  category: {cat.choice} (conf {cat.confidence:.2f})  "
                  + "  ".join(f"{k} {v:.2f}" for k, v in top2))
            print(f"  churn:   {response.nouls['churn_risk'].noul:.2f}  "
                  f"security: {response.nouls['security_concern'].noul:.2f}")
            print(f"  billing: {response.nouls['billing'].noul:.2f}")
            print(f"  tone:    {tone.choice} (conf {tone.confidence:.2f})  "
                  + "  ".join(f"{k} {v:.2f}" for k, v in tone.probabilities.items()))
            print(f"  urgency: {urgency.score:.2f} (conf {urgency.confidence:.2f})  "
                  + "  ".join(f"{urgency.legend.get(k, k)} {v:.2f}"
                              for k, v in sorted(urgency.probabilities.items())))


if __name__ == "__main__":
    main()
