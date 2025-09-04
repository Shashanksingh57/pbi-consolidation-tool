# analyzers/similarity.py - Dashboard similarity analysis and consolidation grouping

import logging
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

from models import (
    DashboardProfile, SimilarityScore, SimilarityBreakdown,
    ConsolidationGroup, ConsolidationRecommendation
)
from analyzers.metadata_processor import MetadataProcessor

logger = logging.getLogger(__name__)

class SimilarityEngine:
    """Engine for calculating dashboard similarity and generating consolidation recommendations"""
    
    def __init__(self):
        self.metadata_processor = MetadataProcessor()
        
        # Default weights for similarity calculation
        self.default_weights = {
            'measures': 0.4,
            'visuals': 0.3,
            'data_model': 0.2,
            'layout': 0.1
        }
        
        # Thresholds for consolidation recommendations
        self.consolidation_thresholds = {
            'merge': 0.85,      # High similarity - merge dashboards
            'review': 0.70,     # Medium similarity - review for consolidation
            'ignore': 0.50      # Low similarity - keep separate
        }
    
    def compare_all_dashboards(self, profiles: List[DashboardProfile], 
                             weights: Dict[str, float] = None) -> List[SimilarityScore]:
        """
        Compare all dashboard pairs and calculate similarity scores
        """
        if weights is None:
            weights = self.default_weights
        
        logger.info(f"Comparing {len(profiles)} dashboards (total pairs: {len(profiles) * (len(profiles) - 1) // 2})")
        
        similarity_scores = []
        
        # Compare each pair of dashboards
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                score = self.compare_dashboards(profiles[i], profiles[j], weights)
                similarity_scores.append(score)
        
        # Sort by similarity score (highest first)
        similarity_scores.sort(key=lambda x: x.total_score, reverse=True)
        
        logger.info(f"Completed similarity analysis: {len(similarity_scores)} comparisons")
        return similarity_scores
    
    def compare_dashboards(self, dashboard1: DashboardProfile, dashboard2: DashboardProfile,
                          weights: Dict[str, float] = None) -> SimilarityScore:
        """
        Compare two dashboards and calculate detailed similarity score
        """
        if weights is None:
            weights = self.default_weights
        
        # Calculate component similarities
        measures_score = self._compare_measures(dashboard1.measures, dashboard2.measures)
        visuals_score = self._compare_visuals(dashboard1.visual_elements, dashboard2.visual_elements)
        data_model_score = self._compare_data_model(dashboard1.tables, dashboard2.tables)
        layout_score = self._compare_layout(dashboard1.visual_elements, dashboard2.visual_elements)
        filters_score = self._compare_filters(dashboard1.visual_elements, dashboard2.visual_elements)
        
        # Calculate weighted total score
        total_score = (
            measures_score * weights.get('measures', 0.4) +
            visuals_score * weights.get('visuals', 0.3) +
            data_model_score * weights.get('data_model', 0.2) +
            layout_score * weights.get('layout', 0.1)
        )
        
        # Create breakdown
        breakdown = SimilarityBreakdown(
            measures_score=measures_score,
            visuals_score=visuals_score,
            data_model_score=data_model_score,
            layout_score=layout_score,
            filters_score=filters_score
        )
        
        # Create similarity score object
        return SimilarityScore(
            dashboard1_id=dashboard1.dashboard_id,
            dashboard2_id=dashboard2.dashboard_id,
            dashboard1_name=dashboard1.dashboard_name,
            dashboard2_name=dashboard2.dashboard_name,
            total_score=total_score,
            breakdown=breakdown
        )
    
    def _compare_measures(self, measures1: List, measures2: List) -> float:
        """Compare DAX measures between dashboards"""
        if not measures1 and not measures2:
            return 1.0
        if not measures1 or not measures2:
            return 0.0
        
        # Create measure name sets for quick lookup
        names1 = {measure.measure_name.lower() for measure in measures1}
        names2 = {measure.measure_name.lower() for measure in measures2}
        
        # Calculate name overlap
        name_overlap = len(names1.intersection(names2))
        total_unique = len(names1.union(names2))
        name_similarity = name_overlap / total_unique if total_unique > 0 else 0.0
        
        # Detailed formula comparison for matching measures
        formula_similarities = []
        for measure1 in measures1:
            for measure2 in measures2:
                if measure1.measure_name.lower() == measure2.measure_name.lower():
                    comparison = self.metadata_processor.compare_measures(measure1, measure2)
                    formula_similarities.append(comparison['overall_similarity'])
        
        formula_similarity = sum(formula_similarities) / len(formula_similarities) if formula_similarities else 0.0
        
        # Weighted combination
        return name_similarity * 0.6 + formula_similarity * 0.4
    
    def _compare_visuals(self, visuals1: List, visuals2: List) -> float:
        """Compare visual elements between dashboards"""
        if not visuals1 and not visuals2:
            return 1.0
        if not visuals1 or not visuals2:
            return 0.0
        
        # Count visual types
        types1 = defaultdict(int)
        types2 = defaultdict(int)
        
        for visual in visuals1:
            types1[visual.visual_type] += 1
        
        for visual in visuals2:
            types2[visual.visual_type] += 1
        
        # Calculate visual type similarity
        all_types = set(types1.keys()).union(set(types2.keys()))
        type_similarities = []
        
        for vtype in all_types:
            count1 = types1.get(vtype, 0)
            count2 = types2.get(vtype, 0)
            
            if count1 == count2 == 0:
                continue
            elif count1 == 0 or count2 == 0:
                type_similarities.append(0.0)
            else:
                # Normalized difference
                max_count = max(count1, count2)
                similarity = 1.0 - abs(count1 - count2) / max_count
                type_similarities.append(similarity)
        
        visual_type_similarity = sum(type_similarities) / len(type_similarities) if type_similarities else 0.0
        
        # Compare data fields used
        fields1 = set()
        fields2 = set()
        
        for visual in visuals1:
            fields1.update(visual.data_fields)
        
        for visual in visuals2:
            fields2.update(visual.data_fields)
        
        field_overlap = len(fields1.intersection(fields2))
        total_fields = len(fields1.union(fields2))
        field_similarity = field_overlap / total_fields if total_fields > 0 else 0.0
        
        # Weighted combination
        return visual_type_similarity * 0.6 + field_similarity * 0.4
    
    def _compare_data_model(self, tables1: List, tables2: List) -> float:
        """Compare data models between dashboards"""
        if not tables1 and not tables2:
            return 1.0
        if not tables1 or not tables2:
            return 0.0
        
        # Extract table names
        names1 = {table.table_name.lower() for table in tables1}
        names2 = {table.table_name.lower() for table in tables2}
        
        # Calculate table name overlap
        overlap = len(names1.intersection(names2))
        total_unique = len(names1.union(names2))
        
        return overlap / total_unique if total_unique > 0 else 0.0
    
    def _compare_layout(self, visuals1: List, visuals2: List) -> float:
        """Compare layout patterns between dashboards"""
        if not visuals1 and not visuals2:
            return 1.0
        if not visuals1 or not visuals2:
            return 0.0
        
        # Compare number of visuals per page
        pages1 = defaultdict(int)
        pages2 = defaultdict(int)
        
        for visual in visuals1:
            pages1[visual.page_name] += 1
        
        for visual in visuals2:
            pages2[visual.page_name] += 1
        
        # Calculate page count similarity
        page_counts1 = sorted(pages1.values())
        page_counts2 = sorted(pages2.values())
        
        if not page_counts1 and not page_counts2:
            return 1.0
        if not page_counts1 or not page_counts2:
            return 0.0
        
        # Simple comparison of page structures
        min_length = min(len(page_counts1), len(page_counts2))
        if min_length == 0:
            return 0.0
        
        similarities = []
        for i in range(min_length):
            count1, count2 = page_counts1[i], page_counts2[i]
            if count1 == count2:
                similarities.append(1.0)
            else:
                max_count = max(count1, count2)
                similarity = 1.0 - abs(count1 - count2) / max_count
                similarities.append(similarity)
        
        # Penalty for different number of pages
        length_penalty = min_length / max(len(page_counts1), len(page_counts2))
        
        return (sum(similarities) / len(similarities)) * length_penalty if similarities else 0.0
    
    def _compare_filters(self, visuals1: List, visuals2: List) -> float:
        """Compare filter elements between dashboards"""
        # Extract filter visuals
        filters1 = [v for v in visuals1 if v.visual_type == 'filter']
        filters2 = [v for v in visuals2 if v.visual_type == 'filter']
        
        if not filters1 and not filters2:
            return 1.0
        if not filters1 or not filters2:
            return 0.0
        
        # Extract filter fields
        fields1 = set()
        fields2 = set()
        
        for filter_visual in filters1:
            fields1.update(filter_visual.data_fields)
        
        for filter_visual in filters2:
            fields2.update(filter_visual.data_fields)
        
        # Calculate overlap
        overlap = len(fields1.intersection(fields2))
        total_unique = len(fields1.union(fields2))
        
        return overlap / total_unique if total_unique > 0 else 0.0
    
    def generate_consolidation_groups(self, profiles: List[DashboardProfile], 
                                    similarity_scores: List[SimilarityScore]) -> List[ConsolidationGroup]:
        """
        Generate consolidation groups based on similarity scores
        """
        logger.info("Generating consolidation groups")
        
        # Create adjacency list for high-similarity dashboards
        connections = defaultdict(set)
        
        for score in similarity_scores:
            if score.total_score >= self.consolidation_thresholds['review']:
                connections[score.dashboard1_id].add(score.dashboard2_id)
                connections[score.dashboard2_id].add(score.dashboard1_id)
        
        # Find connected components (groups)
        visited = set()
        groups = []
        
        for profile in profiles:
            if profile.dashboard_id not in visited:
                group = self._find_connected_group(profile.dashboard_id, connections, visited)
                if len(group) > 1:  # Only create groups with multiple dashboards
                    groups.append(group)
        
        # Create ConsolidationGroup objects
        consolidation_groups = []
        profile_lookup = {p.dashboard_id: p for p in profiles}
        
        for i, group_ids in enumerate(groups):
            # Calculate average similarity within group
            group_similarities = []
            for score in similarity_scores:
                if score.dashboard1_id in group_ids and score.dashboard2_id in group_ids:
                    group_similarities.append(score.total_score)
            
            avg_similarity = sum(group_similarities) / len(group_similarities) if group_similarities else 0.0
            
            # Generate recommendation
            recommendation = self._generate_recommendation(group_ids, avg_similarity, profile_lookup)
            
            # Create group
            group = ConsolidationGroup(
                group_id=f"group_{i+1}",
                dashboard_ids=list(group_ids),
                dashboard_names=[profile_lookup[did].dashboard_name for did in group_ids],
                average_similarity=avg_similarity,
                recommendation=recommendation
            )
            
            consolidation_groups.append(group)
        
        logger.info(f"Generated {len(consolidation_groups)} consolidation groups")
        return consolidation_groups
    
    def _find_connected_group(self, start_id: str, connections: Dict[str, set], visited: set) -> set:
        """Find all dashboards connected to the starting dashboard"""
        if start_id in visited:
            return set()
        
        group = set()
        stack = [start_id]
        
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            
            visited.add(current_id)
            group.add(current_id)
            
            # Add connected dashboards
            for connected_id in connections.get(current_id, set()):
                if connected_id not in visited:
                    stack.append(connected_id)
        
        return group
    
    def _generate_recommendation(self, group_ids: List[str], avg_similarity: float,
                               profile_lookup: Dict[str, DashboardProfile]) -> ConsolidationRecommendation:
        """Generate consolidation recommendation for a group"""
        
        # Determine action based on similarity
        if avg_similarity >= self.consolidation_thresholds['merge']:
            action = "merge"
            reason = f"High similarity ({avg_similarity:.2f}) indicates these dashboards are nearly identical and should be merged."
            effort = "medium"
            priority = 5
        elif avg_similarity >= self.consolidation_thresholds['review']:
            action = "consolidate"
            reason = f"Medium similarity ({avg_similarity:.2f}) suggests consolidation opportunities exist."
            effort = "high"
            priority = 3
        else:
            action = "review"
            reason = f"Some similarity ({avg_similarity:.2f}) detected - manual review recommended."
            effort = "low"
            priority = 1
        
        # Adjust based on group characteristics
        group_profiles = [profile_lookup[gid] for gid in group_ids]
        
        # Factor in complexity
        total_measures = sum(len(p.measures) for p in group_profiles)
        total_visuals = sum(len(p.visual_elements) for p in group_profiles)
        
        if total_measures > 50 or total_visuals > 100:
            if effort == "medium":
                effort = "high"
            priority = max(1, priority - 1)  # Lower priority for complex consolidations
        
        return ConsolidationRecommendation(
            action=action,
            reason=reason,
            effort_estimate=effort,
            priority=priority
        )
    
    def analyze_batch(self, dashboard_profiles: List[DashboardProfile], 
                     weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Perform complete batch analysis on a list of dashboard profiles
        """
        try:
            logger.info(f"Starting batch analysis for {len(dashboard_profiles)} dashboards")
            
            # Calculate similarity scores for all pairs
            similarity_scores = self.compare_all_dashboards(dashboard_profiles, weights)
            
            # Generate consolidation groups
            consolidation_groups = []
            if similarity_scores:
                consolidation_groups = self.generate_consolidation_groups(
                    dashboard_profiles, similarity_scores
                )
            
            # Generate summary statistics
            summary = self._generate_batch_summary(
                dashboard_profiles, similarity_scores, consolidation_groups
            )
            
            logger.info(f"Batch analysis completed: {len(similarity_scores)} similarity scores, "
                       f"{len(consolidation_groups)} consolidation groups")
            
            return {
                'similarity_scores': similarity_scores,
                'consolidation_groups': consolidation_groups,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {str(e)}")
            return {
                'similarity_scores': [],
                'consolidation_groups': [],
                'summary': {}
            }
    
    def _generate_batch_summary(self, dashboard_profiles: List[DashboardProfile],
                              similarity_scores: List[SimilarityScore],
                              consolidation_groups: List[ConsolidationGroup]) -> Dict[str, Any]:
        """Generate summary statistics for batch analysis"""
        
        # Overall statistics
        total_dashboards = len(dashboard_profiles)
        total_views = sum(d.total_pages for d in dashboard_profiles)
        total_measures = sum(len(d.measures) for d in dashboard_profiles)
        total_visuals = sum(len(d.visual_elements) for d in dashboard_profiles)
        
        # Similarity statistics
        high_similarity_pairs = len([s for s in similarity_scores if s.total_score >= 0.85])
        medium_similarity_pairs = len([s for s in similarity_scores if 0.70 <= s.total_score < 0.85])
        low_similarity_pairs = len([s for s in similarity_scores if s.total_score < 0.70])
        
        avg_similarity = sum(s.total_score for s in similarity_scores) / len(similarity_scores) if similarity_scores else 0
        
        # Consolidation statistics
        merge_groups = len([g for g in consolidation_groups if g.recommendation.action == "merge"])
        review_groups = len([g for g in consolidation_groups if g.recommendation.action == "review"])
        
        # Potential reduction
        dashboards_in_merge_groups = sum(len(g.dashboard_ids) for g in consolidation_groups if g.recommendation.action == "merge")
        potential_reduction = dashboards_in_merge_groups - merge_groups if merge_groups > 0 else 0
        
        return {
            'total_dashboards': total_dashboards,
            'total_views': total_views,
            'total_measures': total_measures,
            'total_visuals': total_visuals,
            'similarity_analysis': {
                'total_pairs': len(similarity_scores),
                'high_similarity': high_similarity_pairs,
                'medium_similarity': medium_similarity_pairs,
                'low_similarity': low_similarity_pairs,
                'average_similarity': avg_similarity
            },
            'consolidation_potential': {
                'merge_groups': merge_groups,
                'review_groups': review_groups,
                'potential_dashboard_reduction': potential_reduction,
                'reduction_percentage': (potential_reduction / total_dashboards * 100) if total_dashboards > 0 else 0
            }
        }