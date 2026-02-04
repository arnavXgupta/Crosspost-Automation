import unittest

from app.core.validators import ContentValidator


class TestValidators(unittest.TestCase):
    def test_twitter_validation_ok(self):
        ok, errors = ContentValidator.validate_twitter_thread(["Hook tweet", "Value tweet", "CTA tweet #tag1 #tag2"])
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_twitter_validation_too_long(self):
        tweet = "x" * 281
        ok, errors = ContentValidator.validate_twitter_thread([tweet])
        self.assertFalse(ok)
        self.assertTrue(any("exceeds 280" in e for e in errors))

    def test_linkedin_validation_ok(self):
        ok, errors = ContentValidator.validate_linkedin_post("Hello world", ["#a", "#b"])
        self.assertTrue(ok)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

