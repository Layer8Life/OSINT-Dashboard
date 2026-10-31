from collector.geo import _key


def test_key_strips_possessive_but_keeps_trailing_s():
    assert _key("Paris") == "paris"
    assert _key("Texas'") == "texas"
    assert _key("Sudan’s") == "sudan"
    assert _key("the Netherlands") == "netherlands"
