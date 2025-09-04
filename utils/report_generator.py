# utils/report_generator.py - Report generation utilities

import json
import io
import logging
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

from models import DashboardProfile, SimilarityScore, ConsolidationGroup

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate consolidation reports in various formats"""
    
    def __init__(self):
        pass
    
    def generate_json_report(self, profiles: Dict[str, DashboardProfile], 
                           similarity_scores: List[SimilarityScore],
                           consolidation_groups: List[ConsolidationGroup]) -> Dict[str, Any]:
        """Generate a comprehensive JSON report"""
        
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'tool_version': '1.0.0',
                'dashboards_analyzed': len(profiles),
                'similarity_comparisons': len(similarity_scores),
                'consolidation_groups': len(consolidation_groups)
            },
            'executive_summary': self._generate_executive_summary(profiles, similarity_scores, consolidation_groups),
            'dashboard_profiles': self._serialize_profiles(profiles),
            'similarity_matrix': self._generate_similarity_matrix(similarity_scores),
            'consolidation_recommendations': self._serialize_consolidation_groups(consolidation_groups),
            'detailed_analysis': self._generate_detailed_analysis(profiles, similarity_scores, consolidation_groups)
        }
        
        return report
    
    async def generate_excel_report(self, profiles: Dict[str, DashboardProfile],
                                  similarity_scores: List[SimilarityScore],
                                  consolidation_groups: List[ConsolidationGroup]) -> bytes:
        """Generate Excel report with multiple worksheets"""
        
        try:
            # Create Excel writer
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Executive Summary sheet
                summary_df = self._create_summary_dataframe(profiles, similarity_scores, consolidation_groups)
                summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
                
                # Dashboard Inventory sheet
                inventory_df = self._create_inventory_dataframe(profiles)
                inventory_df.to_excel(writer, sheet_name='Dashboard Inventory', index=False)
                
                # Similarity Matrix sheet
                similarity_df = self._create_similarity_dataframe(similarity_scores)
                similarity_df.to_excel(writer, sheet_name='Similarity Matrix', index=False)
                
                # Consolidation Groups sheet
                groups_df = self._create_groups_dataframe(consolidation_groups)
                groups_df.to_excel(writer, sheet_name='Consolidation Groups', index=False)
                
                # Detailed Measures Comparison
                measures_df = self._create_measures_comparison_dataframe(profiles, similarity_scores)
                measures_df.to_excel(writer, sheet_name='Measures Comparison', index=False)
                
                # Action Items sheet
                actions_df = self._create_action_items_dataframe(consolidation_groups)
                actions_df.to_excel(writer, sheet_name='Action Items', index=False)
            
            output.seek(0)
            return output.read()
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {str(e)}")
            raise
    
    def _generate_executive_summary(self, profiles: Dict[str, DashboardProfile],
                                  similarity_scores: List[SimilarityScore],
                                  consolidation_groups: List[ConsolidationGroup]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        # Calculate key metrics
        total_dashboards = len(profiles)
        high_similarity_pairs = len([s for s in similarity_scores if s.total_score >= 0.85])
        medium_similarity_pairs = len([s for s in similarity_scores if 0.70 <= s.total_score < 0.85])
        
        # Consolidation potential
        dashboards_in_groups = len(set(
            dashboard_id 
            for group in consolidation_groups 
            for dashboard_id in group.dashboard_ids
        ))
        
        consolidation_savings = dashboards_in_groups - len(consolidation_groups) if consolidation_groups else 0
        
        # Effort estimates
        effort_breakdown = {'low': 0, 'medium': 0, 'high': 0}
        for group in consolidation_groups:
            effort_breakdown[group.recommendation.effort_estimate] += 1
        
        return {
            'total_dashboards': total_dashboards,
            'similarity_analysis': {
                'high_similarity_pairs': high_similarity_pairs,
                'medium_similarity_pairs': medium_similarity_pairs,
                'total_comparisons': len(similarity_scores)
            },
            'consolidation_opportunity': {
                'dashboards_eligible': dashboards_in_groups,
                'groups_identified': len(consolidation_groups),
                'potential_reduction': consolidation_savings,
                'reduction_percentage': (consolidation_savings / total_dashboards * 100) if total_dashboards > 0 else 0
            },
            'effort_distribution': effort_breakdown,
            'recommendations': {
                'immediate_action': len([g for g in consolidation_groups if g.recommendation.priority >= 4]),
                'review_needed': len([g for g in consolidation_groups if g.recommendation.priority >= 2]),
                'monitor': len([g for g in consolidation_groups if g.recommendation.priority < 2])
            }
        }
    
    def _generate_similarity_matrix(self, similarity_scores: List[SimilarityScore]) -> List[Dict[str, Any]]:
        """Generate similarity matrix for visualization"""
        matrix_data = []
        
        for score in similarity_scores:
            matrix_data.append({
                'dashboard1': score.dashboard1_name,
                'dashboard2': score.dashboard2_name,
                'total_score': round(score.total_score, 3),
                'measures_score': round(score.breakdown.measures_score, 3),
                'visuals_score': round(score.breakdown.visuals_score, 3),
                'data_model_score': round(score.breakdown.data_model_score, 3),
                'layout_score': round(score.breakdown.layout_score, 3)
            })
        
        return matrix_data
    
    def _generate_detailed_analysis(self, profiles: Dict[str, DashboardProfile],
                                  similarity_scores: List[SimilarityScore],
                                  consolidation_groups: List[ConsolidationGroup]) -> Dict[str, Any]:
        """Generate detailed analysis section"""
        
        analysis = {
            'dashboard_complexity': {},
            'common_patterns': {},
            'consolidation_impact': {}
        }
        
        # Dashboard complexity analysis
        for profile_id, profile in profiles.items():
            complexity = {
                'measures_count': len(profile.measures),
                'visuals_count': len(profile.visual_elements),
                'tables_count': len(profile.tables),
                'pages_count': profile.total_pages,
                'complexity_score': self._calculate_complexity_score(profile)
            }
            analysis['dashboard_complexity'][profile.dashboard_name] = complexity
        
        # Common patterns analysis
        all_visual_types = {}
        all_measure_names = set()
        all_table_names = set()
        
        for profile in profiles.values():
            # Visual types
            for visual in profile.visual_elements:
                vtype = visual.visual_type
                all_visual_types[vtype] = all_visual_types.get(vtype, 0) + 1
            
            # Measure names
            for measure in profile.measures:
                all_measure_names.add(measure.measure_name.lower())
            
            # Table names
            for table in profile.tables:
                all_table_names.add(table.table_name.lower())
        
        analysis['common_patterns'] = {
            'most_common_visuals': sorted(all_visual_types.items(), key=lambda x: x[1], reverse=True)[:10],
            'unique_measures': len(all_measure_names),
            'unique_tables': len(all_table_names),
            'avg_visuals_per_dashboard': sum(len(p.visual_elements) for p in profiles.values()) / len(profiles)
        }
        
        # Consolidation impact
        for group in consolidation_groups:
            group_profiles = [profiles[pid] for pid in group.dashboard_ids if pid in profiles]
            
            impact = {
                'dashboards_count': len(group_profiles),
                'total_measures': sum(len(p.measures) for p in group_profiles),
                'total_visuals': sum(len(p.visual_elements) for p in group_profiles),
                'estimated_effort': group.recommendation.effort_estimate,
                'priority': group.recommendation.priority,
                'potential_maintenance_reduction': len(group_profiles) - 1
            }
            
            analysis['consolidation_impact'][group.group_id] = impact
        
        return analysis
    
    def _serialize_profiles(self, profiles: Dict[str, DashboardProfile]) -> Dict[str, Dict[str, Any]]:
        """Serialize dashboard profiles for JSON output"""
        serialized = {}
        
        for profile_id, profile in profiles.items():
            serialized[profile_id] = {
                'dashboard_name': profile.dashboard_name,
                'created_at': profile.created_at.isoformat(),
                'visual_elements_count': len(profile.visual_elements),
                'measures_count': len(profile.measures),
                'tables_count': len(profile.tables),
                'pages_count': profile.total_pages,
                'complexity_score': self._calculate_complexity_score(profile)
            }
        
        return serialized
    
    def _serialize_consolidation_groups(self, groups: List[ConsolidationGroup]) -> List[Dict[str, Any]]:
        """Serialize consolidation groups for JSON output"""
        serialized = []
        
        for group in groups:
            serialized.append({
                'group_id': group.group_id,
                'dashboard_count': len(group.dashboard_ids),
                'dashboard_names': group.dashboard_names,
                'average_similarity': round(group.average_similarity, 3),
                'recommendation': {
                    'action': group.recommendation.action,
                    'reason': group.recommendation.reason,
                    'effort_estimate': group.recommendation.effort_estimate,
                    'priority': group.recommendation.priority
                },
                'created_at': group.created_at.isoformat()
            })
        
        return serialized
    
    def _calculate_complexity_score(self, profile: DashboardProfile) -> float:
        """Calculate a complexity score for a dashboard"""
        score = 0
        
        # Visual complexity
        score += len(profile.visual_elements) * 0.5
        
        # Measure complexity
        score += len(profile.measures) * 1.0
        
        # Data model complexity
        score += len(profile.tables) * 0.8
        score += len(profile.relationships) * 0.3
        
        # Page complexity
        score += profile.total_pages * 2.0
        
        return round(score, 2)
    
    def _create_summary_dataframe(self, profiles: Dict[str, DashboardProfile],
                                similarity_scores: List[SimilarityScore],
                                consolidation_groups: List[ConsolidationGroup]) -> pd.DataFrame:
        """Create summary dataframe for Excel report"""
        
        summary = self._generate_executive_summary(profiles, similarity_scores, consolidation_groups)
        
        data = [
            ['Total Dashboards', summary['total_dashboards']],
            ['High Similarity Pairs', summary['similarity_analysis']['high_similarity_pairs']],
            ['Medium Similarity Pairs', summary['similarity_analysis']['medium_similarity_pairs']],
            ['Consolidation Groups', summary['consolidation_opportunity']['groups_identified']],
            ['Potential Dashboard Reduction', summary['consolidation_opportunity']['potential_reduction']],
            ['Reduction Percentage', f"{summary['consolidation_opportunity']['reduction_percentage']:.1f}%"],
            ['Immediate Action Groups', summary['recommendations']['immediate_action']],
            ['Review Needed Groups', summary['recommendations']['review_needed']]
        ]
        
        return pd.DataFrame(data, columns=['Metric', 'Value'])
    
    def _create_inventory_dataframe(self, profiles: Dict[str, DashboardProfile]) -> pd.DataFrame:
        """Create dashboard inventory dataframe"""
        
        data = []
        for profile in profiles.values():
            data.append({
                'Dashboard Name': profile.dashboard_name,
                'Dashboard ID': profile.dashboard_id,
                'Visual Elements': len(profile.visual_elements),
                'Measures': len(profile.measures),
                'Tables': len(profile.tables),
                'Pages': profile.total_pages,
                'Complexity Score': self._calculate_complexity_score(profile),
                'Created': profile.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return pd.DataFrame(data)
    
    def _create_similarity_dataframe(self, similarity_scores: List[SimilarityScore]) -> pd.DataFrame:
        """Create similarity scores dataframe"""
        
        data = []
        for score in similarity_scores:
            data.append({
                'Dashboard 1': score.dashboard1_name,
                'Dashboard 2': score.dashboard2_name,
                'Total Similarity': round(score.total_score, 3),
                'Measures Similarity': round(score.breakdown.measures_score, 3),
                'Visuals Similarity': round(score.breakdown.visuals_score, 3),
                'Data Model Similarity': round(score.breakdown.data_model_score, 3),
                'Layout Similarity': round(score.breakdown.layout_score, 3),
                'Computed At': score.computed_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return pd.DataFrame(data)
    
    def _create_groups_dataframe(self, consolidation_groups: List[ConsolidationGroup]) -> pd.DataFrame:
        """Create consolidation groups dataframe"""
        
        data = []
        for group in consolidation_groups:
            data.append({
                'Group ID': group.group_id,
                'Dashboard Count': len(group.dashboard_ids),
                'Dashboard Names': ', '.join(group.dashboard_names),
                'Average Similarity': round(group.average_similarity, 3),
                'Recommended Action': group.recommendation.action,
                'Effort Estimate': group.recommendation.effort_estimate,
                'Priority': group.recommendation.priority,
                'Reason': group.recommendation.reason
            })
        
        return pd.DataFrame(data)
    
    def _create_measures_comparison_dataframe(self, profiles: Dict[str, DashboardProfile],
                                           similarity_scores: List[SimilarityScore]) -> pd.DataFrame:
        """Create measures comparison dataframe"""
        
        data = []
        
        # Get high similarity pairs for detailed measure comparison
        high_sim_pairs = [s for s in similarity_scores if s.total_score >= 0.7]
        
        for score in high_sim_pairs[:10]:  # Limit to top 10 for readability
            profile1 = profiles.get(score.dashboard1_id)
            profile2 = profiles.get(score.dashboard2_id)
            
            if profile1 and profile2:
                measures1_names = {m.measure_name.lower() for m in profile1.measures}
                measures2_names = {m.measure_name.lower() for m in profile2.measures}
                
                common_measures = measures1_names.intersection(measures2_names)
                
                data.append({
                    'Dashboard 1': score.dashboard1_name,
                    'Dashboard 2': score.dashboard2_name,
                    'Measures in Dashboard 1': len(measures1_names),
                    'Measures in Dashboard 2': len(measures2_names),
                    'Common Measures': len(common_measures),
                    'Unique to Dashboard 1': len(measures1_names - measures2_names),
                    'Unique to Dashboard 2': len(measures2_names - measures1_names),
                    'Measure Overlap %': round((len(common_measures) / len(measures1_names.union(measures2_names)) * 100), 1) if measures1_names.union(measures2_names) else 0
                })
        
        return pd.DataFrame(data)
    
    def _create_action_items_dataframe(self, consolidation_groups: List[ConsolidationGroup]) -> pd.DataFrame:
        """Create action items dataframe"""
        
        data = []
        
        # Sort groups by priority (highest first)
        sorted_groups = sorted(consolidation_groups, key=lambda x: x.recommendation.priority, reverse=True)
        
        for i, group in enumerate(sorted_groups, 1):
            data.append({
                'Action Item #': i,
                'Group ID': group.group_id,
                'Priority': group.recommendation.priority,
                'Action': group.recommendation.action.title(),
                'Dashboards': ', '.join(group.dashboard_names),
                'Effort Required': group.recommendation.effort_estimate.title(),
                'Similarity Score': round(group.average_similarity, 3),
                'Rationale': group.recommendation.reason,
                'Status': 'Pending'
            })
        
        return pd.DataFrame(data)