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

    def test_backup_is_serialized_and_release_bound(self):
        source = (ROOT / "operations/backup/n8n-recovery-backup.sh").read_text()
        first_docker = source.index("docker exec")
        self.assertLess(source.index('flock -n 9'), first_docker)
        self.assertLess(source.index('CODESTRA_RELEASE_SHA is required'), first_docker)
        self.assertIn('PRODUCTION_IMAGE_DIGEST=$CODESTRA_N8N_PRODUCTION_IMAGE_DIGEST', source)
        self.assertIn('STAGING_IMAGE_DIGEST=$CODESTRA_N8N_STAGING_IMAGE_DIGEST', source)
        self.assertIn('mv "$publish" "$final"', source)
        self.assertIn('sync -d "$backup_root"', source)

    def test_service_allows_only_named_plaintext_work_path(self):
        unit = (ROOT / "operations/systemd/codestra-n8n-recovery-backup.service").read_text()
        self.assertIn('/run/codestra/n8n-recovery-work', unit)
        self.assertNotRegex(unit, r"(?m)^ReadWritePaths=/\s*$")

    def test_restore_is_fail_closed_and_evidence_bound(self):
        source = (ROOT / "operations/backup/verify-n8n-recovery.sh").read_text()
        for marker in (
            'ALLOW_ISOLATED_N8N_RESTORE',
            'keys.isdisjoint(overrides)',
            'restore database must be empty',
            "('workflow_entity','credentials_entity','migrations')",
            'BACKUP_SHA256=$archive_digest',
            'RESTORE=PASS',
            'flock -n 8',
            'sync -d "$N8N_RESTORE_EVIDENCE_DIR"',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
