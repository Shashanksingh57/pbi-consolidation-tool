"""
PBI Tools Wrapper for Local Batch Processing
Integrates with pbi-tools CLI for extracting metadata from .pbix/.pbit files
"""
import os
import json
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile
import shutil
from models import DashboardProfile, DAXMeasure, DataTable, Relationship

class PBIToolsWrapper:
    """Wrapper for pbi-tools CLI operations"""

    def __init__(self, pbi_tools_path: Optional[str] = None):
        """
        Initialize PBI Tools wrapper
        Args:
            pbi_tools_path: Path to pbi-tools executable. If None, assumes it's in PATH
        """
        self.pbi_tools_path = pbi_tools_path or "pbi-tools"
        self.is_windows = platform.system() == "Windows"

        if not self.is_windows:
            raise OSError("pbi-tools only runs on Windows. For Mac/Linux, use Power BI Service API mode.")

    def check_installation(self) -> bool:
        """Check if pbi-tools is installed and accessible"""
        # Try multiple possible locations and commands
        possible_paths = [
            self.pbi_tools_path,
            "pbi-tools.exe",
            "C:\\pbi-tools\\pbi-tools.exe",
            "C:\\pbi-tools\\pbi-tools"
        ]

        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True  # Use shell to inherit PATH
                )
                if result.returncode == 0:
                    self.pbi_tools_path = path  # Update to working path
                    return True
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return False

    def discover_pbi_files(self, folder_path: str) -> List[Dict[str, str]]:
        """
        Discover all .pbix and .pbit files in a folder and subfolders

        Args:
            folder_path: Root folder to search

        Returns:
            List of dictionaries with file info
        """
        pbi_files = []
        folder = Path(folder_path)

        # Search for .pbix and .pbit files
        for pattern in ["*.pbix", "*.pbit"]:
            for file_path in folder.rglob(pattern):
                pbi_files.append({
                    "name": file_path.stem,
                    "path": str(file_path),
                    "type": file_path.suffix[1:],  # Remove the dot
                    "size_mb": file_path.stat().st_size / (1024 * 1024),
                    "modified": file_path.stat().st_mtime,
                    "relative_path": str(file_path.relative_to(folder))
                })

        return sorted(pbi_files, key=lambda x: x["name"])

    def extract_metadata(self, pbix_path: str) -> Tuple[Dict, Optional[str]]:
        """
        Extract metadata from a .pbix/.pbit file using pbi-tools

        Args:
            pbix_path: Path to the Power BI file

        Returns:
            Tuple of (metadata dict, error message if any)
        """
        metadata = {
            "file_name": Path(pbix_path).stem,
            "measures": [],
            "tables": [],
            "relationships": [],
            "pages": [],
            "data_sources": [],
            "extraction_status": "pending"
        }

        try:
            # Create temp directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the .pbix file
                extract_result = subprocess.run(
                    [self.pbi_tools_path, "extract", pbix_path, "-extractFolder", temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if extract_result.returncode != 0:
                    return metadata, f"Extraction failed: {extract_result.stderr}"

                # Parse extracted files
                metadata.update(self._parse_extracted_files(temp_dir))
                metadata["extraction_status"] = "success"

                return metadata, None

        except subprocess.TimeoutExpired:
            metadata["extraction_status"] = "timeout"
            return metadata, "Extraction timed out after 60 seconds"
        except Exception as e:
            metadata["extraction_status"] = "error"
            return metadata, str(e)

    def _parse_extracted_files(self, extract_dir: str) -> Dict:
        """Parse the extracted pbi-tools output files"""
        parsed_data = {
            "measures": [],
            "tables": [],
            "relationships": [],
            "pages": [],
            "data_sources": []
        }

        # Parse Model/model.bim for measures, tables, relationships
        model_path = Path(extract_dir) / "Model" / "model.bim"
        if model_path.exists():
            with open(model_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)

                # Extract measures
                if "model" in model_data and "tables" in model_data["model"]:
                    for table in model_data["model"]["tables"]:
                        if "measures" in table:
                            for measure in table["measures"]:
                                parsed_data["measures"].append({
                                    "name": measure.get("name", ""),
                                    "expression": measure.get("expression", ""),
                                    "table": table.get("name", ""),
                                    "description": measure.get("description", ""),
                                    "format": measure.get("formatString", "")
                                })

                        # Extract table info
                        parsed_data["tables"].append({
                            "name": table.get("name", ""),
                            "columns": len(table.get("columns", [])),
                            "rows": table.get("rowCount", 0)
                        })

                # Extract relationships
                if "model" in model_data and "relationships" in model_data["model"]:
                    for rel in model_data["model"]["relationships"]:
                        parsed_data["relationships"].append({
                            "from_table": rel.get("fromTable", ""),
                            "from_column": rel.get("fromColumn", ""),
                            "to_table": rel.get("toTable", ""),
                            "to_column": rel.get("toColumn", ""),
                            "type": rel.get("crossFilteringBehavior", "single")
                        })

        # Parse Report/report.json for pages and visuals
        report_path = Path(extract_dir) / "Report" / "report.json"
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

                if "sections" in report_data:
                    for section in report_data["sections"]:
                        page_info = {
                            "name": section.get("displayName", section.get("name", "")),
                            "visuals": [],
                            "filters": []
                        }

                        # Count visual types
                        if "visualContainers" in section:
                            visual_types = {}
                            for container in section["visualContainers"]:
                                if "config" in container:
                                    try:
                                        config = json.loads(container["config"])
                                        visual_type = config.get("singleVisual", {}).get("visualType", "unknown")
                                        visual_types[visual_type] = visual_types.get(visual_type, 0) + 1
                                    except:
                                        pass

                            page_info["visuals"] = [
                                {"type": vtype, "count": count}
                                for vtype, count in visual_types.items()
                            ]

                        parsed_data["pages"].append(page_info)

        # Parse DataSources
        datasources_path = Path(extract_dir) / "Model" / "datasources.json"
        if datasources_path.exists():
            with open(datasources_path, 'r', encoding='utf-8') as f:
                ds_data = json.load(f)
                for ds in ds_data:
                    parsed_data["data_sources"].append({
                        "type": ds.get("type", "unknown"),
                        "kind": ds.get("kind", ""),
                        "connection": ds.get("connectionString", "")[:100]  # Truncate for security
                    })

        return parsed_data

    def batch_extract(self, pbi_files: List[Dict[str, str]],
                     progress_callback=None) -> List[Dict]:
        """
        Extract metadata from multiple PBI files

        Args:
            pbi_files: List of file dictionaries from discover_pbi_files
            progress_callback: Optional callback function(current, total, file_name)

        Returns:
            List of extraction results
        """
        results = []
        total_files = len(pbi_files)

        for idx, file_info in enumerate(pbi_files):
            if progress_callback:
                progress_callback(idx + 1, total_files, file_info["name"])

            metadata, error = self.extract_metadata(file_info["path"])

            results.append({
                "file_info": file_info,
                "metadata": metadata,
                "error": error,
                "requires_screenshot": True  # Flag for UI to collect screenshots
            })

        return results

    def convert_to_dashboard_profile(self, extracted_data: Dict,
                                    screenshot_path: Optional[str] = None) -> DashboardProfile:
        """
        Convert extracted pbi-tools data to DashboardProfile format

        Args:
            extracted_data: Metadata extracted from PBI file
            screenshot_path: Optional path to dashboard screenshot

        Returns:
            DashboardProfile instance
        """
        # Convert measures
        measures = [
            DAXMeasure(
                measure_name=m["name"],
                dax_formula=m["expression"],
                table_name=m["table"],
                description=m.get("description"),
                format_string=m.get("format")
            )
            for m in extracted_data.get("measures", [])
        ]

        # Convert tables
        tables = [
            DataTable(
                table_name=t["name"],
                column_count=t.get("columns", 0),
                row_count=t.get("rows", 0)
            )
            for t in extracted_data.get("tables", [])
        ]

        # Convert relationships
        relationships = [
            Relationship(
                from_table=r["from_table"],
                from_column=r["from_column"],
                to_table=r["to_table"],
                to_column=r["to_column"],
                cardinality=r.get("type", "single")
            )
            for r in extracted_data.get("relationships", [])
        ]

        # Extract visual summary from pages
        visual_elements = []
        for page in extracted_data.get("pages", []):
            for visual in page.get("visuals", []):
                visual_elements.extend([visual["type"]] * visual["count"])

        return DashboardProfile(
            dashboard_id=extracted_data["file_name"],
            dashboard_name=extracted_data["file_name"],
            measures=measures,
            tables=tables,
            relationships=relationships,
            processing_metadata={
                "extraction_method": "pbi-tools",
                "pages": extracted_data.get("pages", []),
                "data_sources": extracted_data.get("data_sources", []),
                "screenshot_path": screenshot_path
            }
        )


class MockPBIToolsWrapper(PBIToolsWrapper):
    """Mock implementation for testing on non-Windows platforms"""

    def __init__(self):
        self.is_windows = False  # Override for testing
        self.pbi_tools_path = "mock-pbi-tools"

    def check_installation(self) -> bool:
        return True

    def discover_pbi_files(self, folder_path: str) -> List[Dict[str, str]]:
        """Return mock PBI files for testing"""
        return [
            {
                "name": "Sales Dashboard",
                "path": f"{folder_path}/Sales Dashboard.pbix",
                "type": "pbix",
                "size_mb": 12.5,
                "modified": 1695000000,
                "relative_path": "Sales Dashboard.pbix"
            },
            {
                "name": "Finance Report",
                "path": f"{folder_path}/Finance Report.pbix",
                "type": "pbix",
                "size_mb": 8.3,
                "modified": 1695100000,
                "relative_path": "Finance Report.pbix"
            },
            {
                "name": "HR Analytics",
                "path": f"{folder_path}/HR Analytics.pbit",
                "type": "pbit",
                "size_mb": 5.1,
                "modified": 1695200000,
                "relative_path": "HR Analytics.pbit"
            }
        ]

    def extract_metadata(self, pbix_path: str) -> Tuple[Dict, Optional[str]]:
        """Return mock extracted metadata"""
        file_name = Path(pbix_path).stem

        metadata = {
            "file_name": file_name,
            "measures": [
                {
                    "name": f"Total {file_name} Amount",
                    "expression": f"SUM([{file_name}].[Amount])",
                    "table": file_name,
                    "description": f"Sum of {file_name} amounts",
                    "format": "#,##0"
                },
                {
                    "name": f"Avg {file_name} Value",
                    "expression": f"AVERAGE([{file_name}].[Value])",
                    "table": file_name,
                    "description": f"Average {file_name} value",
                    "format": "#,##0.00"
                }
            ],
            "tables": [
                {"name": file_name, "columns": 10, "rows": 1000},
                {"name": "Date", "columns": 5, "rows": 365},
                {"name": "Region", "columns": 3, "rows": 50}
            ],
            "relationships": [
                {
                    "from_table": file_name,
                    "from_column": "DateKey",
                    "to_table": "Date",
                    "to_column": "DateKey",
                    "type": "single"
                }
            ],
            "pages": [
                {
                    "name": "Overview",
                    "visuals": [
                        {"type": "card", "count": 4},
                        {"type": "columnChart", "count": 2},
                        {"type": "table", "count": 1}
                    ],
                    "filters": []
                },
                {
                    "name": "Details",
                    "visuals": [
                        {"type": "table", "count": 2},
                        {"type": "slicer", "count": 3}
                    ],
                    "filters": []
                }
            ],
            "data_sources": [
                {
                    "type": "SQL",
                    "kind": "SqlServer",
                    "connection": "Server=localhost;Database=Analytics"
                }
            ],
            "extraction_status": "success"
        }

        return metadata, None