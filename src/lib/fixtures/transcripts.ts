import type { Speaker, TranscriptTurn } from "../types";

const SPEAKER: Record<string, Speaker> = {
  Agent: "AGENT",
  Customer: "CUSTOMER",
  System: "SYSTEM",
};

type RawTurn = [ts: string, speaker: keyof typeof SPEAKER, text: string, kind: TranscriptTurn["kind"]];

function turns(raw: RawTurn[]): TranscriptTurn[] {
  return raw.map(([timestamp, speaker, text, kind]) => ({
    timestamp,
    speaker: SPEAKER[speaker],
    text,
    kind,
  }));
}

/** Speaker-separated, word-level-timestamped transcript excerpts, keyed by lead id. */
export const TRANSCRIPTS: Record<string, TranscriptTurn[]> = {
  "3613742": turns([
    ["00:12", "Agent", "This call is being recorded for quality and compliance purposes.", "pass"],
    ["14:02", "Agent", "Peak is thirty-one point nine cents per kilowatt hour, off-peak is lower.", "pass"],
    ["22:10", "Agent", "Reading your email back: j dot smith at gmail dot com.", "pass"],
  ]),
  "3613790": turns([
    ["00:12", "Agent", "This call is being recorded for quality and compliance purposes. Do you consent to the recording?", "pass"],
    ["02:41", "Customer", "Yes, that's me — I'm the account holder on the bill.", "pass"],
    ["09:55", "Agent", "I need to read you the Default Market Offer comparison in full before we go further.", "pass"],
    ["14:02", "Agent", "So your peak usage will be charged at twenty-eight point six cents per kilowatt hour.", "fail"],
    ["18:30", "System", "[silence 18:30 → 19:17 · 47s dead air]", "note"],
    ["22:10", "Agent", "Let me read that back — j dot smith at g-m-i-a-l dot com, is that right?", "fail"],
    ["25:40", "Agent", "Here are the terms and conditions that apply to this plan.", "pass"],
    ["26:58", "Agent", "You have a ten business day cooling-off period from today.", "pass"],
  ]),
  "3613803": turns([
    ["03:20", "Agent", "That's unit four, twelve Barker Street — correct?", "fail"],
    ["04:05", "Customer", "Date of birth is the eleventh of March, nineteen eighty-eight.", "pass"],
  ]),
  "3613811": turns([
    ["00:12", "Agent", "This call is being recorded for quality and compliance purposes.", "pass"],
    ["09:48", "Agent", "The Default Market Offer for your [crosstalk] compared to the plan we discussed…", "review"],
    ["10:06", "Customer", "Sorry — say that again, the line dropped out for a second.", "review"],
    ["17:05", "Agent", "Is anyone at the property registered for life support equipment?", "pass"],
  ]),
  "3613824": turns([
    ["00:10", "Agent", "This call is being recorded for quality and compliance purposes.", "pass"],
    ["12:14", "System", "[silence 12:14 → 12:52 · 38s dead air]", "note"],
    ["19:30", "Agent", "Your connection date is confirmed for the twenty-fourth.", "pass"],
  ]),
  "3613766": turns([
    ["14:02", "Agent", "Peak is thirty point nine cents per kilowatt hour.", "fail"],
    ["27:40", "Customer", "My paperwork says thirty-one point nine, not thirty point nine.", "note"],
    ["27:52", "Agent", "You're right — sorry, that's thirty-one point nine cents peak.", "pass"],
  ]),
  "3613778": turns([
    ["00:04", "Agent", "Hi, am I speaking with the account holder? Great, let's look at your bill.", "fail"],
    ["02:10", "Customer", "Sure, I've got it here in front of me.", "pass"],
    ["06:12", "Agent", "Can you read me the NMI from the top right of that bill?", "pass"],
  ]),
};
