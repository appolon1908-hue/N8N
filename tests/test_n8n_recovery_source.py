import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class N8nRecoverySourceTests(unittest.TestCase):
    def test_backup_plaintext_is_confined_to_verified_tmpfs(self):
        source = (ROOT / "operations/backup/n8n-recovery-backup.sh").read_text()
        self.assertIn('work_root=${CODESTRA_N8N_BACKUP_WORK_ROOT:-/run/codestra/n8n-recovery-work}', source)
        self.assertIn('stat -f -c %T "$work_root"', source)
        self.assertIn('== "tmpfs"', source)
        self.assertIn('mktemp -d "$work_root/', source)
        self.assertNotIn('mktemp -d "$backup_root/.work-', source)
        self.assertIn('SIGNED-MANIFEST.sig', source)
        self.assertIn('--detach-sign', source)

    def test_backup_is_serialized_and_release_bound(self):
        source = (ROOT / "operations/backup/n8n-recovery-backup.sh").read_text()
        first_docker = source.index("docker exec")
        self.assertLess(source.index('flock -n 9'), first_docker)
        self.assertLess(source.index('CODESTRA_RELEASE_SHA is required'), first_docker)
        self.assertIn('PRODUCTION_IMAGE_DIGEST=$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST', source)
        self.assertIn('STAGING_IMAGE_DIGEST=$CODESTRA_N8N_STAGING_IMAGE_DIGEST', source)
        self.assertIn('production_image_digest_mismatch', source)
        self.assertIn('staging_image_digest_mismatch', source)
        self.assertIn('"n8nio/n8n@$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST"', source)
        self.assertIn('"n8nio/n8n@$CODESTRA_N8N_STAGING_IMAGE_DIGEST"', source)
        self.assertLess(source.index('production_image_digest_mismatch'), first_docker)
        self.assertIn('mv "$publish" "$final"', source)
        self.assertIn('sync -d "$backup_root"', source)

    def test_retention_trusts_only_authenticated_recovery_sets(self):
        source = (ROOT / "operations/backup/n8n-recovery-backup.sh").read_text()
        retention = source[source.index('mapfile -t complete_recoveries'):]
        self.assertIn('SIGNED-MANIFEST.sig', retention)
        self.assertIn('VALIDSIG', retention)
        self.assertIn('CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT', retention)
        self.assertIn('sha256sum -c SIGNED-MANIFEST', retention)
        self.assertLess(retention.index('VALIDSIG'), retention.index('RECOVERY_CAPTURE=PASS'))

    def test_service_allows_only_named_plaintext_work_path(self):
        unit = (ROOT / "operations/systemd/codestra-n8n-recovery-backup.service").read_text()
        self.assertIn('/run/codestra/n8n-recovery-work', unit)
        self.assertIn('RuntimeDirectory=codestra/n8n-recovery-work', unit)
        self.assertIn('RuntimeDirectoryMode=0700', unit)
        self.assertNotRegex(unit, r"(?m)^ReadWritePaths=/\s*$")

    def test_rollout_provisions_required_nonsecret_identity_names(self):
        example = (ROOT / "operations/backup/database-certification.env.example").read_text()
        readme = (ROOT / "operations/README.md").read_text()
        for name in (
            'CODESTRA_DATABASE_BACKUP_GPG_SIGNING_FINGERPRINT',
            'CODESTRA_RELEASE_SHA',
            'CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST',
            'CODESTRA_N8N_STAGING_IMAGE_DIGEST',
        ):
            self.assertIn(name, example)
        self.assertIn('database-certification.env.example', readme)
        self.assertIn('must not be enabled or\nrestarted until that preflight succeeds', readme)

    def test_restore_is_fail_closed_and_evidence_bound(self):
        source = (ROOT / "operations/backup/verify-n8n-recovery.sh").read_text()
        for marker in (
            'ALLOW_ISOLATED_N8N_RESTORE',
            'keys.isdisjoint(overrides)',
            "('workflow_entity','credentials_entity','migrations')",
            'BACKUP_SHA256=$archive_digest',
            'RESTORE=PASS',
            'flock -n 8',
            'sync -d "$N8N_RESTORE_EVIDENCE_DIR"',
        ):
            self.assertIn(marker, source)
        self.assertIn('plaintext recovery work root must be tmpfs', source)
        self.assertIn('CODESTRA_EXPECTED_RELEASE_SHA', source)
        self.assertIn('VALIDSIG', source)
        self.assertIn('restore database contains user objects', source)
        self.assertLess(source.index('recovery release SHA mismatch'), source.index('--decrypt'))
        self.assertLess(source.index('restore database contains user objects'), source.index('pg_restore --list'))

    def test_database_certifier_is_fixed_and_narrowly_delegated(self):
        wrapper = (ROOT / "operations/backup/codestra-n8n-database-certify").read_text()
        sudoers = (ROOT / "operations/sudoers/codestra-n8n-database-certify").read_text()
        self.assertIn('[[ $# -eq 1 && "$1" == "certify" ]]', wrapper)
        self.assertIn("config=/etc/codestra/backup/database-certification.env", wrapper)
        self.assertIn("backup_root=/opt/codestra/backups/n8n-recovery", wrapper)
        self.assertIn("evidence_root=/opt/codestra/backups/n8n-restore-evidence", wrapper)
        self.assertIn('ALLOW_ISOLATED_N8N_RESTORE=true', wrapper)
        self.assertIn('restored_stamp" != "$backup_stamp', wrapper)
        self.assertIn('restore evidence is not bound to the latest backup', wrapper)
        self.assertNotIn("eval ", wrapper)
        self.assertNotIn("sudo ", wrapper)
        rules = [line for line in sudoers.splitlines() if line and not line.startswith("#")]
        self.assertEqual(
            rules,
            ["codestra-admin ALL=(root) NOPASSWD: /usr/local/sbin/codestra-n8n-database-certify certify"],
        )

    def test_backup_and_restore_freshness_are_metadata_bound(self):
        backup = (ROOT / "operations/backup/check-n8n-backup-freshness.sh").read_text()
        restore = (ROOT / "operations/backup/check-n8n-recovery-freshness.sh").read_text()
        self.assertIn('VALIDSIG', backup)
        self.assertIn('backup marker does not match signed status', backup)
        self.assertIn('restore marker does not match verified result', restore)


if __name__ == "__main__":
    unittest.main()
