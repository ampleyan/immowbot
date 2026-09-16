import tempfile
import unittest
from pathlib import Path

from src.buyer.database import load_database_settings


class DatabaseSettingsTest(unittest.TestCase):
    def test_local_mode_uses_unix_socket_not_tcp(self):
        settings = load_database_settings(
            {"DATABASE_MODE": "local", "DATABASE_PASSWORD": "test-password"}
        )

        self.assertEqual(settings.mode, "local")
        self.assertIn("host=/var/run/postgresql", settings.dsn)
        self.assertIn("dbname=immotool", settings.dsn)
        self.assertIn("user=immotool", settings.dsn)
        self.assertNotIn("host=kodisrv", settings.dsn)

    def test_remote_mode_requires_verified_tls(self):
        with self.assertRaisesRegex(ValueError, "sslmode=verify-full"):
            load_database_settings(
                {
                    "DATABASE_MODE": "remote",
                    "DATABASE_DSN": "host=kodisrv dbname=immotool user=immotool",
                }
            )

    def test_remote_mode_rejects_non_kodisrv_host(self):
        with tempfile.TemporaryDirectory() as directory:
            ca_file = Path(directory, "ca.crt")
            ca_file.write_text("test certificate")
            with self.assertRaisesRegex(ValueError, "host"):
                load_database_settings(
                    {
                        "DATABASE_MODE": "remote",
                        "DATABASE_DSN": (
                            f"host=database.example dbname=immotool user=immotool "
                            f"sslmode=verify-full sslrootcert={ca_file}"
                        ),
                    }
                )

    def test_invalid_or_unset_mode_fails_without_sqlite_fallback(self):
        for environ in ({}, {"DATABASE_MODE": "sqlite"}):
            with self.assertRaisesRegex(ValueError, "DATABASE_MODE"):
                load_database_settings(environ)


if __name__ == "__main__":
    unittest.main()
