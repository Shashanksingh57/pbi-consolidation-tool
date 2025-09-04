# analyzers/dax_analyzer.py - DAX and metadata processing

import csv
import io
import re
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from models import DAXMeasure, DataTable, DataSource, Relationship

logger = logging.getLogger(__name__)

class DAXAnalyzer:
    """Analyzes DAX formulas and dashboard metadata"""
    
    def __init__(self):
        self.dax_functions = self._load_dax_functions()
    
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
    
    async def parse_dax_studio_export(self, csv_content: str) -> Dict[str, Any]:
        """
        Parse DAX Studio export CSV and extract measures, tables, relationships
        """
        try:
            logger.info("Parsing DAX Studio export")
            
            # Read CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            
            measures = []
            tables = {}
            relationships = []
            data_sources = []
            
            # Process each row based on ObjectType
            for row in rows:
                object_type = row.get('ObjectType', '').lower()
                
                if object_type == 'measure':
                    measure = self._parse_measure(row)
                    if measure:
                        measures.append(measure)
                
                elif object_type == 'table':
                    table = self._parse_table(row)
                    if table:
                        tables[table.table_name] = table
                
                elif object_type == 'relationship':
                    relationship = self._parse_relationship(row)
                    if relationship:
                        relationships.append(relationship)
                
                elif object_type == 'datasource':
                    source = self._parse_data_source(row)
                    if source:
                        data_sources.append(source)
            
            return {
                'measures': measures,
                'tables': list(tables.values()),
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
    
    def _parse_measure(self, row: Dict[str, str]) -> Optional[DAXMeasure]:
        """Parse a measure row from DAX Studio export"""
        try:
            return DAXMeasure(
                measure_name=row.get('ObjectName', ''),
                dax_formula=row.get('Expression', ''),
                table_name=row.get('TableName', ''),
                description=row.get('Description', ''),
                format_string=row.get('FormatString', '')
            )
        except Exception as e:
            logger.warning(f"Error parsing measure: {str(e)}")
            return None
    
    def _parse_table(self, row: Dict[str, str]) -> Optional[DataTable]:
        """Parse a table row from DAX Studio export"""
        try:
            # Extract column information if available
            columns = []
            if 'Columns' in row and row['Columns']:
                columns = row['Columns'].split(',')
            
            return DataTable(
                table_name=row.get('ObjectName', ''),
                column_count=len(columns) if columns else 0,
                row_count=int(row.get('RowCount', 0)) if row.get('RowCount', '').isdigit() else None,
                columns=columns,
                table_type=self._infer_table_type(row.get('ObjectName', ''))
            )
        except Exception as e:
            logger.warning(f"Error parsing table: {str(e)}")
            return None
    
    def _parse_relationship(self, row: Dict[str, str]) -> Optional[Relationship]:
        """Parse a relationship row from DAX Studio export"""
        try:
            return Relationship(
                from_table=row.get('FromTable', ''),
                to_table=row.get('ToTable', ''),
                from_column=row.get('FromColumn', ''),
                to_column=row.get('ToColumn', ''),
                relationship_type=row.get('Cardinality', 'one_to_many').lower()
            )
        except Exception as e:
            logger.warning(f"Error parsing relationship: {str(e)}")
            return None
    
    def _parse_data_source(self, row: Dict[str, str]) -> Optional[DataSource]:
        """Parse a data source row from DAX Studio export"""
        try:
            return DataSource(
                source_name=row.get('ObjectName', ''),
                source_type=row.get('SourceType', ''),
                connection_details={
                    'server': row.get('Server', ''),
                    'database': row.get('Database', ''),
                    'connection_string': row.get('ConnectionString', '')
                }
            )
        except Exception as e:
            logger.warning(f"Error parsing data source: {str(e)}")
            return None
    
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