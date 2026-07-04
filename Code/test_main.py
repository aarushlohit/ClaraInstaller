import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

with patch("subprocess.run") as _:
    import main


class TestRunPs(unittest.TestCase):
    @patch("main.subprocess.run")
    def test_run_ps_basic(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="output\n", stderr="")
        rc, out, err = main.run_ps("Get-Date", show=False)
        self.assertEqual(rc, 0)
        self.assertIn("output", out)
        mock_run.assert_called_once()

    @patch("main.subprocess.run")
    def test_run_ps_show(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="shown\n", stderr="")
        with patch("builtins.print") as mock_print:
            rc, out, err = main.run_ps("Get-Disk", show=True)
            mock_print.assert_any_call("shown\n")

    @patch("main.subprocess.run")
    def test_run_cmd(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="cmdout\n", stderr="")
        rc, out, err = main.run_cmd("dir")
        self.assertEqual(rc, 0)
        self.assertIn("cmdout", out)

    @patch("main.subprocess.run")
    def test_get_ps_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="drive_d\n", stderr="")
        result = main.get_ps_output("Get-Partition | select DriveLetter")
        self.assertEqual(result, "drive_d")


class TestSelectDisk(unittest.TestCase):
    @patch("main.run_ps")
    @patch("builtins.input")
    def test_select_disk_valid(self, mock_input, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")
        mock_input.side_effect = ["1"]

        result = main.select_disk()
        self.assertEqual(result, 1)

    @patch("main.run_ps")
    @patch("builtins.input")
    def test_select_disk_invalid_then_valid(self, mock_input, mock_run_ps):
        mock_run_ps.side_effect = [
            (0, "disk list\n", ""),
            (1, "", ""),
            (0, "disk list\n", ""),
            (0, "", ""),
        ]
        mock_input.side_effect = ["abc", "0"]

        result = main.select_disk()
        self.assertEqual(result, 0)

    @patch("main.run_ps")
    @patch("builtins.input")
    def test_select_disk_wrong_then_correct(self, mock_input, mock_run_ps):
        mock_run_ps.side_effect = [
            (0, "disk list\n", ""),
            (1, "", ""),
            (0, "disk list\n", ""),
            (0, "", ""),
        ]
        mock_input.side_effect = ["2", "1"]

        result = main.select_disk()
        self.assertEqual(result, 1)


class TestSelectSize(unittest.TestCase):
    @patch("builtins.input")
    def test_select_size_valid(self, mock_input):
        mock_input.return_value = "20"
        result = main.select_size()
        self.assertEqual(result, 20)

    @patch("builtins.input")
    def test_select_size_minimum(self, mock_input):
        mock_input.return_value = "10"
        result = main.select_size()
        self.assertEqual(result, 10)

    @patch("builtins.input")
    def test_select_size_too_small_then_valid(self, mock_input):
        mock_input.side_effect = ["5", "15"]
        result = main.select_size()
        self.assertEqual(result, 15)

    @patch("builtins.input")
    def test_select_size_non_numeric_then_valid(self, mock_input):
        mock_input.side_effect = ["abc", "25"]
        result = main.select_size()
        self.assertEqual(result, 25)


class TestShrinkWindows(unittest.TestCase):
    @patch("main.run_ps")
    def test_shrink_success(self, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")
        main.shrink_windows(20)
        mock_run_ps.assert_called_once()

    @patch("main.run_ps")
    @patch("main.sys.exit")
    def test_shrink_failure(self, mock_exit, mock_run_ps):
        mock_run_ps.return_value = (1, "", "")
        main.shrink_windows(10)
        mock_exit.assert_called_once_with(1)


class TestCreateLinuxPartition(unittest.TestCase):
    @patch("main.run_ps")
    @patch("main.get_partition_drive_letter")
    @patch("main.sys.exit")
    def test_create_success(self, mock_exit, mock_get_letter, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")
        mock_get_letter.return_value = "D"

        result = main.create_linux_partition(0, 20)
        self.assertEqual(result, "D")

    @patch("main.run_ps")
    @patch("main.sys.exit")
    def test_create_failure(self, mock_exit, mock_run_ps):
        mock_run_ps.return_value = (1, "", "")
        mock_exit.side_effect = SystemExit(1)
        with self.assertRaises(SystemExit):
            main.create_linux_partition(0, 20)

    @patch("main.run_ps")
    @patch("main.get_partition_drive_letter")
    def test_create_fallback_label(self, mock_get_letter, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")
        mock_get_letter.return_value = ""

        result = main.create_linux_partition(0, 20)
        self.assertEqual(result, main.PARTITION_LABEL)


class TestSelectISOSource(unittest.TestCase):
    @patch("main.os.path.exists")
    @patch("builtins.input")
    def test_local_iso(self, mock_input, mock_exists):
        mock_exists.return_value = True
        mock_input.side_effect = ["1", "/path/to/clara.iso"]
        result = main.select_iso_source()
        self.assertEqual(result, "/path/to/clara.iso")

    @patch("builtins.input")
    def test_default_url(self, mock_input):
        mock_input.side_effect = ["2", ""]
        result = main.select_iso_source()
        self.assertEqual(result, main.DEFAULT_ISO_URL)

    @patch("builtins.input")
    def test_custom_url(self, mock_input):
        mock_input.side_effect = ["2", "https://example.com/custom.iso"]
        result = main.select_iso_source()
        self.assertEqual(result, "https://example.com/custom.iso")


class TestDownloadISO(unittest.TestCase):
    @patch("main.run_ps")
    @patch("main.os.path.getsize")
    @patch("main.os.path.exists")
    def test_iso_local_file(self, mock_exists, mock_getsize, mock_run_ps):
        mock_exists.return_value = True
        mock_getsize.return_value = 3 * 1024 * 1024 * 1024

        result = main.download_iso("/home/user/clara.iso")
        self.assertEqual(result, "/home/user/clara.iso")
        mock_run_ps.assert_not_called()

    @patch("main.run_ps")
    @patch("main.os.path.getsize")
    @patch("main.os.path.exists")
    @patch("main.os.remove")
    def test_iso_already_exists(self, mock_remove, mock_exists, mock_getsize, mock_run_ps):
        local_path = "/tmp/clara-desktop.iso"
        mock_exists.return_value = True
        mock_getsize.return_value = 500 * 1024 * 1024

        result = main.download_iso(local_path)
        self.assertEqual(result, local_path)
        mock_run_ps.assert_not_called()

    @patch("main.run_ps")
    @patch("main.os.path.getsize")
    @patch("main.os.path.exists")
    @patch("main.os.remove")
    def test_iso_partial_redownload(self, mock_remove, mock_exists, mock_getsize, mock_run_ps):
        mock_exists.side_effect = [False, True]
        mock_getsize.return_value = 50 * 1024 * 1024
        mock_run_ps.return_value = (0, "", "")

        result = main.download_iso(main.DEFAULT_ISO_URL)
        self.assertTrue(result.endswith(main.ISO_FILENAME))
        mock_remove.assert_called_once()

    @patch("main.run_ps")
    @patch("main.os.path.getsize")
    @patch("main.os.path.exists")
    def test_iso_download_fresh(self, mock_exists, mock_getsize, mock_run_ps):
        mock_exists.return_value = False
        mock_getsize.return_value = 5 * 1024 * 1024 * 1024
        mock_run_ps.return_value = (0, "", "")

        result = main.download_iso(main.DEFAULT_ISO_URL)
        self.assertTrue(result.endswith(main.ISO_FILENAME))
        mock_run_ps.assert_called_once()

    @patch("main.run_ps")
    @patch("main.os.path.exists")
    @patch("main.sys.exit")
    def test_iso_download_failure(self, mock_exit, mock_exists, mock_run_ps):
        mock_exists.return_value = False
        mock_run_ps.return_value = (1, "", "")
        mock_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit):
            main.download_iso(main.DEFAULT_ISO_URL)


class TestExtractISO(unittest.TestCase):
    @patch("main.run_ps")
    def test_extract_success(self, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")

        result = main.extract_iso("test.iso", "D")
        self.assertTrue(result)
        mock_run_ps.assert_called_once()

    @patch("main.run_ps")
    def test_extract_failure(self, mock_run_ps):
        mock_run_ps.return_value = (1, "", "")

        result = main.extract_iso("test.iso", "D")
        self.assertFalse(result)


class TestDetectFirmware(unittest.TestCase):
    @patch("main.run_ps")
    def test_uefi(self, mock_run_ps):
        mock_run_ps.return_value = (0, "UEFI\n", "")
        result = main.detect_firmware()
        self.assertEqual(result, main.FIRMWARE_UEFI)

    @patch("main.run_ps")
    def test_bios(self, mock_run_ps):
        mock_run_ps.return_value = (0, "BIOS\n", "")
        result = main.detect_firmware()
        self.assertEqual(result, main.FIRMWARE_BIOS)

    @patch("main.run_ps")
    def test_fallback_on_error(self, mock_run_ps):
        mock_run_ps.return_value = (1, "", "")
        result = main.detect_firmware()
        self.assertEqual(result, main.FIRMWARE_BIOS)


class TestLocateEfiFile(unittest.TestCase):
    @patch("main.os.path.exists")
    def test_finds_shim(self, mock_exists):
        mock_exists.side_effect = lambda p: "shimx64.efi" in p
        result = main.locate_efi_file("D")
        self.assertIn("shimx64.efi", result)

    @patch("main.os.path.exists")
    def test_finds_grub(self, mock_exists):
        mock_exists.side_effect = lambda p: "grubx64.efi" in p
        result = main.locate_efi_file("D")
        self.assertIn("grubx64.efi", result)

    @patch("main.os.path.exists")
    def test_finds_bootx64(self, mock_exists):
        mock_exists.side_effect = lambda p: "BOOTX64.EFI" in p
        result = main.locate_efi_file("D")
        self.assertIn("BOOTX64.EFI", result)

    @patch("main.os.path.exists")
    def test_no_efi_found(self, mock_exists):
        mock_exists.return_value = False
        result = main.locate_efi_file("D")
        self.assertIsNone(result)


class TestConfigureEfiBoot(unittest.TestCase):
    @patch("main.run_cmd")
    @patch("main.locate_efi_file")
    def test_efi_configured_with_file(self, mock_locate, mock_run_cmd):
        mock_locate.return_value = "\\EFI\\BOOT\\BOOTX64.EFI"
        mock_run_cmd.return_value = (0, "", "")

        main.configure_efi_boot("D")
        self.assertEqual(mock_run_cmd.call_count, 2)

    @patch("main.run_cmd")
    @patch("main.locate_efi_file")
    @patch("main.run_ps")
    def test_efi_configured_without_file(self, mock_run_ps, mock_locate, mock_run_cmd):
        mock_locate.return_value = None
        mock_run_cmd.return_value = (0, "", "")
        mock_run_ps.return_value = (0, "", "")

        main.configure_efi_boot("D")
        self.assertGreaterEqual(mock_run_cmd.call_count, 1)


class TestConfigureBiosBoot(unittest.TestCase):
    @patch("main._set_partition_active_by_letter")
    @patch("main._run_bootsect")
    def test_bossect_success_partition_active(self, mock_bootsect, mock_active):
        mock_bootsect.return_value = True
        mock_active.return_value = True

        result = main.configure_bios_boot("D")
        self.assertTrue(result)

    @patch("main._set_partition_active_by_letter")
    @patch("main._run_bootsect")
    def test_bootsect_fails_partition_succeeds(self, mock_bootsect, mock_active):
        mock_bootsect.return_value = False
        mock_active.return_value = True

        result = main.configure_bios_boot("D")
        self.assertTrue(result)

    @patch("main._set_partition_active_by_letter")
    @patch("main._run_bootsect")
    def test_both_fail(self, mock_bootsect, mock_active):
        mock_bootsect.return_value = False
        mock_active.return_value = False

        result = main.configure_bios_boot("D")
        self.assertFalse(result)


class TestAddBcdEntry(unittest.TestCase):
    @patch("main.run_cmd")
    @patch("main.locate_efi_file")
    def test_add_bcd_entry_uefi(self, mock_locate, mock_run_cmd):
        mock_locate.return_value = "\\EFI\\boot\\bootx64.efi"
        mock_run_cmd.return_value = (
            0,
            "The entry was created with identifier {abc123-4567-def0-89ab-cdef01234567}.\n",
            ""
        )

        result = main.add_bcd_entry("D", main.FIRMWARE_UEFI)
        self.assertIsNotNone(result)
        self.assertIn("abc123", result)

    @patch("main.run_cmd")
    def test_add_bcd_entry_bios(self, mock_run_cmd):
        mock_run_cmd.return_value = (
            0,
            "The entry was created with identifier {def456-7890-abcd-ef01-234567890abc}.\n",
            ""
        )

        result = main.add_bcd_entry("D", main.FIRMWARE_BIOS)
        self.assertIsNotNone(result)
        self.assertIn("def456", result)

    @patch("main.run_cmd")
    def test_add_bcd_entry_failure(self, mock_run_cmd):
        mock_run_cmd.return_value = (1, "The command failed.\n", "")
        result = main.add_bcd_entry("D", main.FIRMWARE_UEFI)
        self.assertIsNone(result)


class TestAddBcdEntryHelpers(unittest.TestCase):
    @patch("main.run_cmd")
    def test_set_boot_priority(self, mock_run_cmd):
        mock_run_cmd.return_value = (0, "", "")
        main.set_boot_priority("{abc-123}")
        self.assertEqual(mock_run_cmd.call_count, 2)

    @patch("main.get_ps_output")
    def test_get_partition_drive_letter(self, mock_get):
        mock_get.return_value = "E"
        result = main.get_partition_drive_letter(0)
        self.assertEqual(result, "E")

    @patch("main.get_ps_output")
    def test_get_partition_drive_letter_empty(self, mock_get):
        mock_get.return_value = ""
        result = main.get_partition_drive_letter(0)
        self.assertEqual(result, "")


class TestSetBootPriority(unittest.TestCase):
    @patch("main.run_cmd")
    def test_set_boot_priority(self, mock_run_cmd):
        mock_run_cmd.return_value = (0, "", "")
        main.set_boot_priority("{abc-123}")
        self.assertEqual(mock_run_cmd.call_count, 2)


class TestBiosBootHelpers(unittest.TestCase):
    @patch("main.run_cmd")
    def test_run_bootsect_success(self, mock_run_cmd):
        mock_run_cmd.return_value = (0, "", "")
        result = main._run_bootsect("D")
        self.assertTrue(result)

    @patch("main.run_cmd")
    def test_run_bootsect_failure(self, mock_run_cmd):
        mock_run_cmd.return_value = (1, "", "")
        result = main._run_bootsect("D")
        self.assertFalse(result)

    @patch("main.run_ps")
    def test_set_partition_active_success(self, mock_run_ps):
        mock_run_ps.return_value = (0, "", "")
        result = main._set_partition_active_by_letter("D")
        self.assertTrue(result)

    @patch("main.run_ps")
    def test_set_partition_active_failure(self, mock_run_ps):
        mock_run_ps.return_value = (1, "", "")
        result = main._set_partition_active_by_letter("D")
        self.assertFalse(result)


class TestPromptReboot(unittest.TestCase):
    @patch("main.run_cmd")
    @patch("builtins.input")
    def test_reboot_yes(self, mock_input, mock_run_cmd):
        mock_input.return_value = "y"
        mock_run_cmd.return_value = (0, "", "")
        main.prompt_reboot()
        reboot_call = [c for c in mock_run_cmd.call_args_list if "shutdown" in str(c)]
        self.assertTrue(len(reboot_call) > 0)

    @patch("main.run_cmd")
    @patch("builtins.input")
    def test_reboot_no(self, mock_input, mock_run_cmd):
        mock_input.return_value = "n"
        main.prompt_reboot()
        reboot_calls = [c for c in mock_run_cmd.call_args_list if "shutdown" in str(c)]
        self.assertEqual(len(reboot_calls), 0)


class TestConstants(unittest.TestCase):
    def test_constants_defined(self):
        self.assertTrue(main.MIN_SIZE_GB >= 10)
        self.assertEqual(main.PARTITION_LABEL, "LINUXOS")
        self.assertEqual(main.BOOT_DESC, "Clara Desktop Linux")
        self.assertTrue(main.ISO_FILENAME.endswith(".iso"))
        self.assertTrue(main.DEFAULT_ISO_URL.startswith("http"))
        self.assertEqual(main.FIRMWARE_UEFI, "UEFI")
        self.assertEqual(main.FIRMWARE_BIOS, "BIOS")


class TestMainFlow(unittest.TestCase):
    @patch("main.set_boot_priority")
    @patch("main.add_bcd_entry")
    @patch("main.configure_efi_boot")
    @patch("main.configure_bios_boot")
    @patch("main.extract_iso")
    @patch("main.download_iso")
    @patch("main.select_iso_source")
    @patch("main.create_linux_partition")
    @patch("main.shrink_windows")
    @patch("main.select_size")
    @patch("main.select_disk")
    @patch("main.detect_firmware")
    @patch("main.prompt_reboot")
    def test_main_flow_uefi(
        self, mock_reboot, mock_fw, mock_disk, mock_size, mock_shrink,
        mock_part, mock_iso_source, mock_iso, mock_extract, mock_bios_boot,
        mock_efi, mock_bcd, mock_priority
    ):
        mock_fw.return_value = main.FIRMWARE_UEFI
        mock_disk.return_value = 0
        mock_size.return_value = 20
        mock_part.return_value = "D"
        mock_iso_source.return_value = main.DEFAULT_ISO_URL
        mock_iso.return_value = "/tmp/clara-desktop.iso"
        mock_extract.return_value = True
        mock_bcd.return_value = "{guid-123}"
        mock_priority.return_value = None
        mock_reboot.return_value = None

        main.main()

        mock_fw.assert_called_once()
        mock_disk.assert_called_once()
        mock_size.assert_called_once()
        mock_shrink.assert_called_once_with(20)
        mock_part.assert_called_once_with(0, 20)
        mock_iso_source.assert_called_once()
        mock_iso.assert_called_once_with(main.DEFAULT_ISO_URL)
        mock_efi.assert_called_once_with("D")
        mock_bios_boot.assert_not_called()
        mock_bcd.assert_called_once_with("D", main.FIRMWARE_UEFI)
        mock_priority.assert_called_once_with("{guid-123}")

    @patch("main.set_boot_priority")
    @patch("main.add_bcd_entry")
    @patch("main.configure_efi_boot")
    @patch("main.configure_bios_boot")
    @patch("main.extract_iso")
    @patch("main.download_iso")
    @patch("main.select_iso_source")
    @patch("main.create_linux_partition")
    @patch("main.shrink_windows")
    @patch("main.select_size")
    @patch("main.select_disk")
    @patch("main.detect_firmware")
    @patch("main.prompt_reboot")
    def test_main_flow_bios(
        self, mock_reboot, mock_fw, mock_disk, mock_size, mock_shrink,
        mock_part, mock_iso_source, mock_iso, mock_extract, mock_bios_boot,
        mock_efi, mock_bcd, mock_priority
    ):
        mock_fw.return_value = main.FIRMWARE_BIOS
        mock_disk.return_value = 0
        mock_size.return_value = 20
        mock_part.return_value = "D"
        mock_iso_source.return_value = main.DEFAULT_ISO_URL
        mock_iso.return_value = "/tmp/clara-desktop.iso"
        mock_extract.return_value = True
        mock_bcd.return_value = "{guid-456}"

        main.main()

        mock_fw.assert_called_once()
        mock_efi.assert_not_called()
        mock_bios_boot.assert_called_once_with("D")
        mock_bcd.assert_called_once_with("D", main.FIRMWARE_BIOS)

    @patch("main.set_boot_priority")
    @patch("main.add_bcd_entry")
    @patch("main.configure_efi_boot")
    @patch("main.configure_bios_boot")
    @patch("main.extract_iso")
    @patch("main.download_iso")
    @patch("main.select_iso_source")
    @patch("main.create_linux_partition")
    @patch("main.shrink_windows")
    @patch("main.select_size")
    @patch("main.select_disk")
    @patch("main.detect_firmware")
    @patch("main.prompt_reboot")
    def test_main_flow_no_bcd(
        self, mock_reboot, mock_fw, mock_disk, mock_size, mock_shrink,
        mock_part, mock_iso_source, mock_iso, mock_extract, mock_bios_boot,
        mock_efi, mock_bcd, mock_priority
    ):
        mock_fw.return_value = main.FIRMWARE_UEFI
        mock_disk.return_value = 0
        mock_size.return_value = 15
        mock_part.return_value = "E"
        mock_iso_source.return_value = main.DEFAULT_ISO_URL
        mock_iso.return_value = "/tmp/test.iso"
        mock_extract.return_value = True
        mock_bcd.return_value = None

        main.main()

        mock_priority.assert_not_called()


if __name__ == "__main__":
    unittest.main()
