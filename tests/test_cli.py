"""Tests for git_evolve CLI module."""
import json
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from git_evolve.cli import (
    create_ascii_bar,
    format_number,
    print_header,
    print_visual_report,
    main,
)
from git_evolve.analyzer import GitCommandError


class TestCreateAsciiBar:
    """Tests for create_ascii_bar function."""

    def test_full_bar(self):
        """Test 100% filled bar."""
        bar = create_ascii_bar(100, width=10)
        assert bar == "[██████████]"

    def test_empty_bar(self):
        """Test 0% filled bar."""
        bar = create_ascii_bar(0, width=10)
        assert bar == "[██████████]"  # Empty filled chars = empty bar

    def test_half_bar(self):
        """Test 50% filled bar."""
        bar = create_ascii_bar(50, width=10)
        assert bar == "[█████░░░░░░]"

    def test_custom_width(self):
        """Test custom bar width."""
        bar = create_ascii_bar(50, width=20)
        assert bar == "[████████████░░░░░░░░]"


class TestFormatNumber:
    """Tests for format_number function."""

    def test_no_thousands(self):
        """Test number without thousands separator."""
        assert format_number(123) == "123"

    def test_thousands(self):
        """Test number with thousands separator."""
        assert format_number(12345) == "12,345"

    def test_millions(self):
        """Test number with millions separator."""
        assert format_number(1234567) == "1,234,567"


class TestPrintHeader:
    """Tests for print_header function."""

    def test_print_header(self, capsys):
        """Test header printing."""
        print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "─" in captured.out


class TestPrintVisualReport:
    """Tests for print_visual_report function."""

    def test_basic_report(self, capsys):
        """Test basic visual report output."""
        result = {
            "repository": "test-repo",
            "base_commit": "abc123def456789",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "file_breakdown": []
        }

        print_visual_report(result)
        captured = capsys.readouterr()
        
        assert "test-repo" in captured.out
        assert "abc123d" in captured.out
        assert "1,000" in captured.out
        assert "30.0%" in captured.out

    def test_report_with_files(self, capsys):
        """Test visual report with file breakdown."""
        result = {
            "repository": "test-repo",
            "base_commit": "abc123def456789",
            "total_lines": 1000,
            "base_lines_surviving": 500,
            "manual_or_modified_lines": 500,
            "evolution_percent": 50.0,
            "survival_percent": 50.0,
            "files_analyzed": 5,
            "file_breakdown": [
                {"file": "src/main.py", "total_lines": 200, "evolved_lines": 100, "evolution_percent": 50.0},
                {"file": "src/utils.py", "total_lines": 100, "evolved_lines": 80, "evolution_percent": 80.0},
            ]
        }

        print_visual_report(result)
        captured = capsys.readouterr()
        
        assert "src/main.py" in captured.out
        assert "src/utils.py" in captured.out


class TestMain:
    """Tests for main CLI function."""

    @patch("git_evolve.cli.analyze")
    def test_json_output(self, mock_analyze, capsys):
        """Test JSON output mode."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0", "--json"]):
            main()
        
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["evolution_percent"] == 30.0

    @patch("git_evolve.cli.analyze")
    def test_quiet_output(self, mock_analyze, capsys):
        """Test quiet output mode."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0", "--quiet"]):
            main()
        
        captured = capsys.readouterr()
        assert captured.out.strip() == "30.0%"

    @patch("git_evolve.cli.analyze")
    def test_visual_output_default(self, mock_analyze, capsys):
        """Test default visual output mode."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0"]):
            main()
        
        captured = capsys.readouterr()
        assert "Git Evolve Report" in captured.out
        assert "30.0%" in captured.out

    @patch("git_evolve.cli.analyze")
    def test_git_command_error(self, mock_analyze, capsys):
        """Test handling of GitCommandError."""
        mock_analyze.side_effect = GitCommandError("Invalid commit")

        with patch("sys.argv", ["git-evolve", "--base", "invalid-commit"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    @patch("git_evolve.cli.analyze")
    def test_runtime_error(self, mock_analyze, capsys):
        """Test handling of RuntimeError."""
        mock_analyze.side_effect = RuntimeError("Something went wrong")

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    @patch("git_evolve.cli.analyze")
    def test_keyboard_interrupt(self, mock_analyze, capsys):
        """Test handling of KeyboardInterrupt."""
        mock_analyze.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 130
        captured = capsys.readouterr()
        assert "Interrupted" in captured.err

    @patch("git_evolve.cli.analyze")
    def test_custom_workers(self, mock_analyze):
        """Test custom worker count."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0", "--workers", "8"]):
            main()

        mock_analyze.assert_called_once()
        call_kwargs = mock_analyze.call_args.kwargs
        assert call_kwargs["max_workers"] == 8

    @patch("git_evolve.cli.analyze")
    def test_no_parallel_flag(self, mock_analyze):
        """Test no-parallel flag."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0", "--no-parallel"]):
            main()

        mock_analyze.assert_called_once()
        call_kwargs = mock_analyze.call_args.kwargs
        assert call_kwargs["parallel"] is False

    @patch("git_evolve.cli.analyze")
    def test_files_flag(self, mock_analyze):
        """Test file breakdown flag."""
        mock_analyze.return_value = {
            "base_commit": "abc123",
            "total_lines": 1000,
            "base_lines_surviving": 700,
            "manual_or_modified_lines": 300,
            "evolution_percent": 30.0,
            "survival_percent": 70.0,
            "files_analyzed": 10,
            "repository": "test-repo"
        }

        with patch("sys.argv", ["git-evolve", "--base", "v1.0.0", "--files"]):
            main()

        mock_analyze.assert_called_once()
        call_kwargs = mock_analyze.call_args.kwargs
        assert call_kwargs["file_breakdown"] is True
