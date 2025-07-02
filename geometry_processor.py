"""
geometry_processor.py

Geometric processing module for pipeline interference analysis.
Handles trajectory sectionization and distance calculations between OHL and pipeline routes.
"""

import numpy as np

class Sectionizer:
    """
    Processes OHL and pipeline trajectories to create simplified parallel sections.
    """
    def __init__(self, ohl_trajectory, pipeline_trajectory):
        """
        Initializes the Sectionizer.

        Args:
            ohl_trajectory (list of lists): OHL route as [[x1,y1,z1], [x2,y2,z2], ...].
            pipeline_trajectory (list of lists): Pipeline route as [[x1,y1,z1], ...].
        """
        self.ohl_segments = self._create_segments(ohl_trajectory)
        self.pipeline_segments = self._create_segments(pipeline_trajectory)

    def _create_segments(self, trajectory):
        """Converts a list of points into a list of segments (start, end)."""
        return [
            (np.array(trajectory[i]), np.array(trajectory[i+1]))
            for i in range(len(trajectory) - 1)
        ]

    def _get_distance_point_to_line_segment(self, point, line_start, line_end):
        """Calculates the shortest distance from a point to a line segment."""
        line_vec = line_end - line_start
        point_vec = point - line_start
        line_len_sq = np.dot(line_vec, line_vec)
        
        if line_len_sq == 0.0:
            return np.linalg.norm(point_vec)

        # Project point_vec onto line_vec
        t = max(0, min(1, np.dot(point_vec, line_vec) / line_len_sq))
        
        projection = line_start + t * line_vec
        return np.linalg.norm(point - projection)

    def discretize_and_section(self, step_length_m=10):
        """
        Walks along the pipeline route, calculates separation at each step,
        and groups steps into parallel sections.

        Args:
            step_length_m (int): The granularity for walking along the pipeline.

        Returns:
            list of dict: A list of sections, e.g., 
                          [{'length': 1000, 'avg_separation': 50.0}, ...].
        """
        sections = []
        current_section_points = []
        
        total_pl_dist = 0
        for pl_start, pl_end in self.pipeline_segments:
            segment_vec = pl_end - pl_start
            segment_len = np.linalg.norm(segment_vec)
            
            num_steps = int(segment_len / step_length_m)
            if num_steps == 0: 
                num_steps = 1  # Ensure at least one step for very short segments

            for i in range(num_steps + 1):
                # Current point on the pipeline
                if i == num_steps:
                    # Last point should be exactly at the end
                    point_on_pl = pl_end
                else:
                    dist_along_seg = i * step_length_m
                    point_on_pl = pl_start + (segment_vec / segment_len) * dist_along_seg
                
                # Find the shortest distance to any OHL segment
                min_dist = float('inf')
                for ohl_start, ohl_end in self.ohl_segments:
                    dist = self._get_distance_point_to_line_segment(
                        point_on_pl, ohl_start, ohl_end
                    )
                    if dist < min_dist:
                        min_dist = dist
                
                current_section_points.append(min_dist)
            
            # Create a section for this pipeline segment
            if current_section_points:
                avg_separation = np.mean(current_section_points)
                section_length = segment_len
                sections.append({
                    'length_m': section_length,
                    'avg_separation_m': avg_separation
                })
                total_pl_dist += section_length
                current_section_points = []
        
        print(f"--- Sectionizer Results ---")
        print(f"Total pipeline length processed: {total_pl_dist / 1000:.2f} km")
        for i, sec in enumerate(sections):
            print(f"  Section {i+1}: Length={sec['length_m']:.0f}m, Avg. Separation={sec['avg_separation_m']:.2f}m")
        print("-" * 27)
        
        return sections
