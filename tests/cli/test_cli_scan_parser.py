from astanalyzer.cli import build_parser


def test_scan_parser_accepts_rule_filter_arguments():
    parser = build_parser()

    args = parser.parse_args([
        "scan",
        ".",
        "--only", "STYLE-002,STYLE-003",
        "--exclude", "SEC-031",
        "--only-category", "STYLE",
        "--exclude-category", "SECURITY",
        "--exclude-dir", "tests,migrations",
    ])

    assert args.command == "scan"
    assert args.path == "."
    assert args.only == "STYLE-002,STYLE-003"
    assert args.exclude == "SEC-031"
    assert args.only_category == "STYLE"
    assert args.exclude_category == "SECURITY"
    assert args.exclude_dir == "tests,migrations"