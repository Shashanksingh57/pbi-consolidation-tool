# analyzers/metadata_processor.py - Dashboard metadata processing for both local files and API

import csv
import io
import re
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from models import DAXMeasure, DataTable, DataSource, Relationship

logger = logging.getLogger(__name__)

class MetadataProcessor:
    """Processes dashboard metadata from both local files and Power BI API"""
    
    def __init__(self):
        self.dax_functions = self._load_dax_functions()
    
    def _get_case_insensitive_value(self, row: Dict[str, str], key: str) -> str:
        """Get value from row dictionary using case-insensitive key matching"""
        for actual_key, value in row.items():
            if actual_key.lower() == key.lower():
                return value.strip()
        return ''
    
    def _load_dax_functions(self) -> set:
        """Load common DAX functions for analysis"""
        return {
            'SUM', 'SUMX', 'AVERAGE', 'AVERAGEX', 'COUNT', 'COUNTX', 'COUNTA', 'COUNTAX',
            'COUNTROWS', 'DISTINCTCOUNT', 'MIN', 'MAX', 'CALCULATE', 'FILTER',
            'ALL', 'ALLEXCEPT', 'VALUES', 'DISTINCT', 'RELATED', 'RELATEDTABLE',
            'DATEADD', 'DATESYTD', 'TOTALYTD', 'SAMEPERIODLASTYEAR', 'PARALLELPERIOD',
            'FORMAT', 'CONCATENATE', 'LEFT', 'RIGHT', 'MID', 'FIND', 'SUBSTITUTE',
            'IF', 'SWITCH', 'AND', 'OR', 'NOT', 'BLANK', 'ISBLANK', 'ISERROR',
            'DIVIDE', 'ROUNDUP', 'ROUNDDOWN', 'ROUND', 'INT', 'MOD', 'ABS',
            'RANKX', 'TOPN', 'EARLIER', 'EARLIEST', 'HASONEVALUE', 'SELECTEDVALUE'
        }
    
    def parse_dax_studio_export(self, csv_content: str) -> Dict[str, Any]:
        """
        Parse DAX Studio export CSV and extract measures, tables, or relationships
        based on column headers to identify file type
        """
        try:
            logger.info("Parsing DAX Studio export - identifying file type by headers")
            
            # Read CSV content and get headers
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            
            # Convert headers to lowercase for case-insensitive matching
            headers = [h.lower() for h in reader.fieldnames or []]
            original_headers = reader.fieldnames or []
            
            logger.info(f"Detected CSV headers: {original_headers}")
            logger.info(f"Lowercase headers for matching: {headers}")
            
            # Initialize return structure
            measures = []
            tables = []
            relationships = []
            data_sources = []
            
            # Robust case-insensitive file identification with specific column headers
            if 'measure_name' in headers and 'expression' in headers:
                logger.info("Identified as measures file")
                measures = self._parse_measures_file(rows)
                
            elif 'tableid' in headers and 'explicitdatatype' in headers:
                logger.info("Identified as tables file")
                tables = self._parse_tables_file(rows)
                
            elif 'fromtableid' in headers and 'totableid' in headers:
                logger.info("Identified as relationships file")
                relationships = self._parse_relationships_file(rows)
                
            else:
                logger.warning(f"Unknown CSV file type. Headers: {original_headers}")
                return {
                    'measures': [],
                    'tables': [],
                    'relationships': [],
                    'data_sources': [],
                    'error': f'Unknown CSV format. Expected headers for measures, tables, or relationships. Got: {original_headers}'
                }
            
            return {
                'measures': measures,
                'tables': tables,
                'relationships': relationships,
                'data_sources': data_sources,
                'summary': {
                    'measures_count': len(measures),
                    'tables_count': len(tables),
                    'relationships_count': len(relationships),
                    'data_sources_count': len(data_sources)
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing DAX Studio export: {str(e)}")
            return {
                'measures': [],
                'tables': [],
                'relationships': [],
                'data_sources': [],
                'error': str(e)
            }
    
    def _parse_measures_file(self, rows: List[Dict[str, str]]) -> List[DAXMeasure]:
        """Parse measures CSV file with headers like MEASURE_NAME, EXPRESSION"""
        measures = []
        try:
            for row in rows:
                measure_name = self._get_case_insensitive_value(row, 'MEASURE_NAME')
                expression = self._get_case_insensitive_value(row, 'EXPRESSION')
                table_name = self._get_case_insensitive_value(row, 'TABLE_NAME')
                description = self._get_case_insensitive_value(row, 'DESCRIPTION')
                format_string = self._get_case_insensitive_value(row, 'FORMAT_STRING')
                
                if measure_name and expression:
                    measure = DAXMeasure(
                        measure_name=measure_name,
                        dax_formula=expression,
                        table_name=table_name or 'Unknown',
                        description=description,
                        format_string=format_string
                    )
                    measures.append(measure)
                    logger.debug(f"Parsed measure: {measure_name}")
                    
        except Exception as e:
            logger.error(f"Error parsing measures file: {str(e)}")
            
        logger.info(f"Parsed {len(measures)} measures from CSV")
        return measures
    
    def _parse_tables_file(self, rows: List[Dict[str, str]]) -> List[DataTable]:
        """Parse tables CSV file - group columns by TableName to create DataTable objects"""
        tables = []
        try:
            # Group rows by TableName since each row represents a column
            table_groups = {}
            for row in rows:
                table_name = self._get_case_insensitive_value(row, 'TableID')
                if table_name:
                    if table_name not in table_groups:
                        table_groups[table_name] = []
                    table_groups[table_name].append(row)
            
            # Create DataTable object for each unique table
            for table_name, column_rows in table_groups.items():
                # Extract column information
                columns = []
                for col_row in column_rows:
                    explicit_name = self._get_case_insensitive_value(col_row, 'ExplicitName')
                    column_name = self._get_case_insensitive_value(col_row, 'Name')
                    # Use ExplicitName if available, otherwise use Name
                    col_name = explicit_name or column_name
                    if col_name and col_name not in columns:
                        columns.append(col_name)
                
                column_count = len(columns)
                
                # Try to get row count from first column entry (if available)
                row_count = None
                if column_rows:
                    row_count_str = self._get_case_insensitive_value(column_rows[0], 'RowCount')
                    try:
                        row_count = int(row_count_str) if row_count_str.isdigit() else None
                    except (ValueError, TypeError):
                        row_count = None
                
                # Create DataTable object
                table = DataTable(
                    table_name=table_name,
                    column_count=column_count,
                    row_count=row_count,
                    columns=columns,
                    table_type=self._infer_table_type(table_name)
                )
                tables.append(table)
                logger.debug(f"Parsed table: {table_name} with {column_count} columns: {columns[:5]}{'...' if len(columns) > 5 else ''}")
                    
        except Exception as e:
            logger.error(f"Error parsing tables file: {str(e)}")
            
        logger.info(f"Parsed {len(tables)} tables from CSV with column grouping")
        return tables
    
    def _parse_relationships_file(self, rows: List[Dict[str, str]]) -> List[Relationship]:
        """Parse relationships CSV file using correct DAX Studio column names"""
        relationships = []
        try:
            for row in rows:
                # Use case-insensitive column access for DAX Studio relationships export
                from_table = self._get_case_insensitive_value(row, 'FromTableID')
                from_column = self._get_case_insensitive_value(row, 'FromColumnID')
                to_table = self._get_case_insensitive_value(row, 'ToTableID')
                to_column = self._get_case_insensitive_value(row, 'ToColumnID')
                
                # Handle various possible cardinality column names (case-insensitive)
                cardinality = (
                    self._get_case_insensitive_value(row, 'Cardinality') or 
                    self._get_case_insensitive_value(row, 'CrossFilteringBehavior') or 
                    self._get_case_insensitive_value(row, 'Multiplicity') or 
                    'one_to_many'
                ).lower()
                
                # Normalize cardinality values
                if 'many' in cardinality and 'one' in cardinality:
                    if cardinality.startswith('many'):
                        cardinality = 'many_to_one'
                    else:
                        cardinality = 'one_to_many'
                elif 'many' in cardinality:
                    cardinality = 'many_to_many'
                elif 'one' in cardinality:
                    cardinality = 'one_to_one'
                else:
                    cardinality = 'one_to_many'  # default
                
                if from_table and to_table and from_column and to_column:
                    relationship = Relationship(
                        from_table=from_table,
                        to_table=to_table,
                        from_column=from_column,
                        to_column=to_column,
                        relationship_type=cardinality
                    )
                    relationships.append(relationship)
                    logger.debug(f"Parsed relationship: {from_table}.{from_column} -> {to_table}.{to_column} ({cardinality})")
                else:
                    logger.warning(f"Incomplete relationship data: FromTable='{from_table}', FromColumn='{from_column}', ToTable='{to_table}', ToColumn='{to_column}'")
                    
        except Exception as e:
            logger.error(f"Error parsing relationships file: {str(e)}")
            
        logger.info(f"Parsed {len(relationships)} relationships from CSV")
        return relationships
    
    
    def _infer_table_type(self, table_name: str) -> str:
        """Infer table type based on naming conventions"""
        table_name_lower = table_name.lower()
        
        # Common dimension table indicators
        dimension_indicators = ['dim', 'dimension', 'lookup', 'master', 'reference']
        if any(indicator in table_name_lower for indicator in dimension_indicators):
            return 'dimension'
        
        # Common fact table indicators
        fact_indicators = ['fact', 'transaction', 'sales', 'order', 'event', 'log']
        if any(indicator in table_name_lower for indicator in fact_indicators):
            return 'fact'
        
        # Bridge table indicators
        bridge_indicators = ['bridge', 'junction', 'association', 'link']
        if any(indicator in table_name_lower for indicator in bridge_indicators):
            return 'bridge'
        
        # Default to fact if unclear
        return 'fact'
    
    def analyze_dax_formula(self, formula: str) -> Dict[str, Any]:
        """
        Analyze a DAX formula and extract key characteristics
        """
        if not formula:
            return {'error': 'Empty formula'}
        
        # Extract DAX functions used
        used_functions = []
        formula_upper = formula.upper()
        
        for func in self.dax_functions:
            if func in formula_upper:
                used_functions.append(func)
        
        # Analyze complexity
        complexity_indicators = {
            'nested_functions': len(re.findall(r'\([^()]*\([^()]*\)', formula)),
            'filter_contexts': len(re.findall(r'CALCULATE|FILTER|ALL', formula_upper)),
            'time_intelligence': len(re.findall(r'DATEADD|DATESYTD|TOTALYTD|SAMEPERIODLASTYEAR', formula_upper)),
            'iterators': len(re.findall(r'SUMX|AVERAGEX|COUNTX|RANKX', formula_upper)),
            'logical_functions': len(re.findall(r'IF|SWITCH|AND|OR|NOT', formula_upper))
        }
        
        # Calculate overall complexity score
        complexity_score = sum(complexity_indicators.values())
        
        # Extract referenced tables/columns
        table_references = re.findall(r"'?([A-Za-z_][A-Za-z0-9_\s]*)'?\[", formula)
        column_references = re.findall(r"\[([A-Za-z_][A-Za-z0-9_\s]*)\]", formula)
        
        return {
            'used_functions': used_functions,
            'complexity_score': complexity_score,
            'complexity_indicators': complexity_indicators,
            'table_references': list(set(table_references)),
            'column_references': list(set(column_references)),
            'formula_length': len(formula),
            'function_count': len(used_functions)
        }
    
    def compare_measures(self, measure1: DAXMeasure, measure2: DAXMeasure) -> Dict[str, Any]:
        """
        Compare two DAX measures for similarity
        """
        # Analyze both formulas
        analysis1 = self.analyze_dax_formula(measure1.dax_formula)
        analysis2 = self.analyze_dax_formula(measure2.dax_formula)
        
        # Calculate similarity scores
        function_similarity = self._calculate_function_similarity(
            analysis1.get('used_functions', []),
            analysis2.get('used_functions', [])
        )
        
        structure_similarity = self._calculate_structure_similarity(
            analysis1.get('complexity_indicators', {}),
            analysis2.get('complexity_indicators', {})
        )
        
        # String similarity (fuzzy matching)
        string_similarity = self._calculate_string_similarity(
            measure1.dax_formula, measure2.dax_formula
        )
        
        # Overall similarity (weighted average)
        overall_similarity = (
            function_similarity * 0.4 +
            structure_similarity * 0.3 +
            string_similarity * 0.3
        )
        
        return {
            'overall_similarity': overall_similarity,
            'function_similarity': function_similarity,
            'structure_similarity': structure_similarity,
            'string_similarity': string_similarity,
            'measure1_analysis': analysis1,
            'measure2_analysis': analysis2
        }
    
    def _calculate_function_similarity(self, functions1: List[str], functions2: List[str]) -> float:
        """Calculate similarity based on DAX functions used"""
        if not functions1 and not functions2:
            return 1.0
        if not functions1 or not functions2:
            return 0.0
        
        set1 = set(functions1)
        set2 = set(functions2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_structure_similarity(self, indicators1: Dict[str, int], indicators2: Dict[str, int]) -> float:
        """Calculate similarity based on formula structure"""
        if not indicators1 and not indicators2:
            return 1.0
        
        # Compare each complexity indicator
        similarities = []
        all_keys = set(indicators1.keys()).union(set(indicators2.keys()))
        
        for key in all_keys:
            val1 = indicators1.get(key, 0)
            val2 = indicators2.get(key, 0)
            
            if val1 == val2 == 0:
                similarities.append(1.0)
            elif val1 == 0 or val2 == 0:
                similarities.append(0.0)
            else:
                # Normalized difference
                max_val = max(val1, val2)
                similarity = 1.0 - abs(val1 - val2) / max_val
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_string_similarity(self, formula1: str, formula2: str) -> float:
        """Calculate string similarity between formulas (simple approach)"""
        if not formula1 and not formula2:
            return 1.0
        if not formula1 or not formula2:
            return 0.0
        
        # Normalize formulas (remove spaces, convert to uppercase)
        norm1 = re.sub(r'\s+', '', formula1.upper())
        norm2 = re.sub(r'\s+', '', formula2.upper())
        
        if norm1 == norm2:
            return 1.0
        
        # Simple character-based similarity
        max_len = max(len(norm1), len(norm2))
        if max_len == 0:
            return 1.0
        
        # Count common characters (basic approach)
        common_chars = 0
        for i in range(min(len(norm1), len(norm2))):
            if norm1[i] == norm2[i]:
                common_chars += 1
        
        return common_chars / max_len
    
    def get_metadata_summary(self, measures: List[DAXMeasure], tables: List[DataTable]) -> Dict[str, Any]:
        """
        Generate summary statistics for dashboard metadata
        """
        # Analyze measures
        measure_complexities = [
            self.analyze_dax_formula(measure.dax_formula).get('complexity_score', 0)
            for measure in measures
        ]
        
        # Analyze functions usage
        all_functions = []
        for measure in measures:
            analysis = self.analyze_dax_formula(measure.dax_formula)
            all_functions.extend(analysis.get('used_functions', []))
        
        function_counts = {}
        for func in all_functions:
            function_counts[func] = function_counts.get(func, 0) + 1
        
        # Table analysis
        table_types = {}
        total_columns = 0
        for table in tables:
            table_type = table.table_type
            table_types[table_type] = table_types.get(table_type, 0) + 1
            total_columns += table.column_count
        
        return {
            'measures': {
                'count': len(measures),
                'avg_complexity': sum(measure_complexities) / len(measure_complexities) if measure_complexities else 0,
                'max_complexity': max(measure_complexities) if measure_complexities else 0,
                'top_functions': sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            'tables': {
                'count': len(tables),
                'total_columns': total_columns,
                'avg_columns': total_columns / len(tables) if tables else 0,
                'table_types': table_types
            },
            'complexity_distribution': {
                'simple': len([c for c in measure_complexities if c <= 2]),
                'medium': len([c for c in measure_complexities if 3 <= c <= 5]),
                'complex': len([c for c in measure_complexities if c > 5])
            }
        }
    
    def analyze_metadata_files(self, metadata_contents: List[str], dashboard_id: str) -> Dict[str, Any]:
        """
        Analyze multiple metadata file contents for a dashboard
        """
        try:
            all_measures = []
            all_tables = []
            all_relationships = []
            all_data_sources = []
            
            for i, csv_content in enumerate(metadata_contents):
                # Parse the CSV file content
                parsed_data = self.parse_dax_studio_export(csv_content)
                
                # Aggregate results
                all_measures.extend(parsed_data.get('measures', []))
                all_tables.extend(parsed_data.get('tables', []))
                all_relationships.extend(parsed_data.get('relationships', []))
                all_data_sources.extend(parsed_data.get('data_sources', []))
                
                logger.info(f"Processed metadata file {i+1} for {dashboard_id}")
            
            return {
                'measures': all_measures,
                'tables': all_tables,
                'relationships': all_relationships,
                'data_sources': all_data_sources,
                'summary': self._generate_metadata_summary(all_measures, all_tables, all_relationships)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing metadata files for {dashboard_id}: {str(e)}")
            return {
                'measures': [],
                'tables': [],
                'relationships': [],
                'data_sources': []
            }
    
    def _generate_metadata_summary(self, measures: List[DAXMeasure], 
                                 tables: List[DataTable], 
                                 relationships: List[Relationship]) -> Dict[str, Any]:
        """Generate summary statistics for metadata"""
        return {
            'total_measures': len(measures),
            'total_tables': len(tables),
            'total_relationships': len(relationships),
            'complexity_score': self._calculate_metadata_complexity(measures, tables, relationships),
            'unique_dax_functions': len(set(
                func for measure in measures 
                for func in self._extract_dax_functions(measure.dax_formula)
            )) if measures else 0
        }
    
    def _calculate_metadata_complexity(self, measures: List[DAXMeasure], 
                                     tables: List[DataTable], 
                                     relationships: List[Relationship]) -> float:
        """Calculate overall metadata complexity score"""
        measure_complexity = sum(self._calculate_dax_complexity(m.dax_formula) for m in measures)
        table_complexity = sum(t.column_count for t in tables)
        relationship_complexity = len(relationships) * 0.5
        
        total_complexity = measure_complexity + table_complexity + relationship_complexity
        return min(total_complexity / 10, 10.0)  # Normalize to 0-10 scale
    
    def _extract_dax_functions(self, formula: str) -> List[str]:
        """Extract DAX functions from a formula"""
        if not formula:
            return []
        
        used_functions = []
        formula_upper = formula.upper()
        
        for func in self.dax_functions:
            if func in formula_upper:
                used_functions.append(func)
        
        return used_functions
    
    def _calculate_dax_complexity(self, formula: str) -> float:
        """Calculate complexity score for a DAX formula"""
        if not formula:
            return 0.0
        
        analysis = self.analyze_dax_formula(formula)
        return analysis.get('complexity_score', 0.0)