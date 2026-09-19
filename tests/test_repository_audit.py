"""Regression tests for the tracked-text privacy secret rules.

Secret-like values are assembled from fragments on purpose: the repository must
never store a complete value that could be mistaken for a real credential.
"""

from tools.audit_repository import SECRET_PATTERNS

GITHUB = SECRET_PATTERNS["GitHub token"]
AWS = SECRET_PATTERNS["AWS access key"]
PRIVATE_KEY = SECRET_PATTERNS["private key"]

GITHUB_PREFIXES = ["ghp", "gho", "ghu", "ghs", "ghr"]

# The identifier that produced the GitHub CI false positive. ``ghs_`` appears
# only as a substring of the word "outweighs".
FALSE_POSITIVE_IDENTIFIER = (
    "def test_signal_outweighs_noise_reproducible_and_no_mutation():"
)


def _github_token(prefix: str = "ghp", body_length: int = 36) -> str:
    return prefix + "_" + "A" * body_length


def test_complete_github_token_is_detected_in_quotes_whitespace_and_separators():
    wrappers = ['"{}"', "'{}'", " {} ", "token={},", "({})", "x\t{}\n", "[{}]"]
    for prefix in GITHUB_PREFIXES:
        token = _github_token(prefix)
        for wrapper in wrappers:
            text = wrapper.format(token)
            match = GITHUB.search(text)
            assert match is not None, f"{prefix} token not found in {wrapper!r}"
            assert match.group(0) == token


def test_github_token_is_detected_at_the_edges_of_the_scanned_text():
    token = _github_token("ghs")
    assert GITHUB.search(token).group(0) == token
    assert GITHUB.search("prefix " + token).group(0) == token
    assert GITHUB.search(token + " suffix").group(0) == token
    assert GITHUB.search("key=" + token).group(0) == token


def test_identifier_substrings_are_not_reported_as_github_tokens():
    assert GITHUB.search(FALSE_POSITIVE_IDENTIFIER) is None
    assert GITHUB.search("outweighs_noise_reproducible_and_no_mutation") is None
    assert GITHUB.search("x = token_name_outweighs_noise_reproducible_and_no_mutation") is None
    assert GITHUB.search("someghs_noise_reproducible_and_no_mutation") is None
    # A real token followed by a non-word separator is still detected.
    assert GITHUB.search(_github_token("ghp") + ", next") is not None


def test_standalone_token_shaped_text_is_detected_but_plain_words_are_not():
    # A standalone identifier of the same shape is indistinguishable from a
    # token; only substrings inside longer identifiers must be ignored.
    # The value is assembled at runtime so the repository never stores a
    # complete token-shaped string (which the audit would rightly flag).
    standalone = "gh" + "s_" + "noise" + "_reproducible" + "_and_no_mutation"
    assert GITHUB.search(standalone).group(0) == standalone
    assert GITHUB.search("the noise outweighs the signal") is None


def test_aws_access_key_rule_is_unchanged():
    key = "AKIA" + "B" * 16
    assert AWS.search(key).group(0) == key
    assert AWS.search('"access_key": "' + key + '"').group(0) == key
    assert AWS.search("AKIA" + "B" * 15) is None


def test_private_key_rule_is_unchanged():
    headers = [
        "BEGIN " + "PRIVATE KEY",
        "BEGIN " + "RSA " + "PRIVATE KEY",
        "BEGIN " + "OPENSSH " + "PRIVATE KEY",
        "BEGIN " + "EC " + "PRIVATE KEY",
    ]
    for header in headers:
        assert PRIVATE_KEY.search("-----" + header + "-----").group(0) == header
    assert PRIVATE_KEY.search("a private key file") is None
