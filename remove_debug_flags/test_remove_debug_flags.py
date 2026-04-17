from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from remove_debug_flags import CleanOptions, run_clean, transform_verilog, transform_vhdl


class RemoveDebugFlagsTests(unittest.TestCase):
    def make_options(self, root: Path | None = None, **kwargs) -> CleanOptions:
        options = CleanOptions(root=root or Path("."), **kwargs)
        return options

    def test_verilog_removes_mark_debug_only(self) -> None:
        source = 'module m;\n(* MARK_DEBUG="true" *)reg [15:0] pix_cnt;\nendmodule\n'
        result, stats = transform_verilog(source, self.make_options())
        self.assertNotIn("MARK_DEBUG", result)
        self.assertIn("reg [15:0] pix_cnt;", result)
        self.assertEqual(stats.mark_debug_removed, 1)

    def test_verilog_removes_companion_dont_touch(self) -> None:
        source = (
            '(* dont_touch="true" *)(* MARK_DEBUG="true" *)reg [15:0] row_cnt;\n'
            '(* dont_touch="true" *)wire keep_me;\n'
        )
        result, stats = transform_verilog(source, self.make_options())
        self.assertIn('(* dont_touch="true" *)wire keep_me;', result)
        self.assertIn("reg [15:0] row_cnt;", result)
        self.assertEqual(stats.mark_debug_removed, 1)
        self.assertEqual(stats.dont_touch_removed, 1)
        self.assertEqual(stats.dont_touch_preserved, 1)

    def test_verilog_keeps_other_attributes_and_ignores_comments(self) -> None:
        source = (
            'assign a = 1\'b0;\n'
            '(* keep="true", MARK_DEBUG = "TRUE" *) wire sig;\n'
            '// (* MARK_DEBUG="true" *) wire comment_sig;\n'
            'initial $display("MARK_DEBUG");\n'
        )
        result, stats = transform_verilog(source, self.make_options())
        self.assertIn('(* keep="true" *) wire sig;', result)
        self.assertIn('// (* MARK_DEBUG="true" *) wire comment_sig;', result)
        self.assertIn('"MARK_DEBUG"', result)
        self.assertEqual(stats.mark_debug_removed, 1)

    def test_vhdl_removes_mark_debug_and_companion_dont_touch(self) -> None:
        source = (
            "attribute mark_debug : string;\n"
            "attribute dont_touch : string;\n"
            "attribute mark_debug of pix_cnt : signal is \"true\";\n"
            "attribute dont_touch of pix_cnt : signal is \"true\";\n"
            "attribute dont_touch of keep_me : signal is \"true\";\n"
        )
        result, stats = transform_vhdl(source, self.make_options())
        self.assertNotIn("mark_debug", result.lower())
        self.assertIn("attribute dont_touch : string;", result)
        self.assertIn("attribute dont_touch of keep_me : signal is \"true\";", result)
        self.assertNotIn("attribute dont_touch of pix_cnt", result)
        self.assertEqual(stats.mark_debug_removed, 2)
        self.assertEqual(stats.dont_touch_removed, 1)

    def test_apply_backup_uses_parallel_debug_version_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rtl_root = Path(temp_dir) / "rtl"
            source_file = rtl_root / "sub" / "demo.v"
            source_file.parent.mkdir(parents=True)
            source_file.write_text('(* MARK_DEBUG="true" *)reg demo;\n', encoding="utf-8")
            report = run_clean(CleanOptions(root=rtl_root, apply_changes=True, create_backup=True), on_log=lambda _msg: None)
            backup_file = Path(temp_dir) / "debug_version" / "sub" / "demo.v.bak"
            self.assertEqual(len(report.changed_files), 1)
            self.assertTrue(backup_file.exists())
            self.assertIn("MARK_DEBUG", backup_file.read_text(encoding="utf-8"))
            self.assertNotIn("MARK_DEBUG", source_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
