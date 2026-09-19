from __future__ import annotations

from app.services.redaction import redact_card_numbers


def test_redacts_a_16_digit_card_number_spoken_with_spaces():
    text, violation = redact_card_numbers("It's 4111 1111 1111 1111 if that helps.")
    assert violation is True
    assert "4111" not in text
    assert "[REDACTED CARD NUMBER]" in text


def test_redacts_a_card_number_spoken_with_dashes():
    text, violation = redact_card_numbers("Card is 4111-1111-1111-1111.")
    assert violation is True
    assert "4111-1111-1111-1111" not in text


def test_does_not_redact_an_ordinary_phone_or_reference_number():
    text, violation = redact_card_numbers("Reference number is 12345, call back on 0412 345 678.")
    assert violation is False
    assert text == "Reference number is 12345, call back on 0412 345 678."


def test_does_not_redact_a_nmi_length_identifier_below_13_digits():
    text, violation = redact_card_numbers("Your NMI is 6305123456.")
    assert violation is False
    assert "6305123456" in text


def test_leaves_ordinary_transcript_text_untouched():
    text, violation = redact_card_numbers("Peak is 31.9 cents per kilowatt hour.")
    assert violation is False
    assert text == "Peak is 31.9 cents per kilowatt hour."
