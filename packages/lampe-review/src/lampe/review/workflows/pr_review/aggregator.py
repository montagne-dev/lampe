"""Review aggregator for merging and deduplicating agent findings."""

from collections import defaultdict
from typing import List

from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
    ReviewComment,
)


class ReviewAggregator:
    """Aggregates reviews from multiple agents and deduplicates findings."""

    def aggregate_reviews(self, agent_reviews: List[AgentReviewOutput]) -> List[FileReview]:
        """Aggregate reviews from all agents into a cohesive output."""
        # Group reviews by file path
        file_reviews = defaultdict(list)

        for agent_output in agent_reviews:
            for file_review in agent_output.reviews:
                file_reviews[file_review.file_path].append(file_review)

        # Merge reviews for each file
        aggregated_reviews = []

        for file_path, reviews in file_reviews.items():
            merged_review = self._merge_file_reviews(file_path, reviews)
            aggregated_reviews.append(merged_review)

        return aggregated_reviews

    def _merge_file_reviews(self, file_path: str, reviews: List[FileReview]) -> FileReview:
        """Merge multiple reviews for the same file."""
        # Combine all line comments
        all_line_comments = {}
        all_structured_comments = []
        all_summaries = []
        agent_names = []

        for review in reviews:
            # Merge line comments
            for line_num, comment in review.line_comments.items():
                if line_num in all_line_comments:
                    # Combine comments from different agents
                    all_line_comments[line_num] += f" [{review.agent_name}]: {comment}"
                else:
                    all_line_comments[line_num] = f"[{review.agent_name}]: {comment}"

            # Collect structured comments
            all_structured_comments.extend(review.structured_comments)

            # Collect summaries
            if review.summary:
                all_summaries.append(f"[{review.agent_name}]: {review.summary}")

            # Collect agent names
            if review.agent_name:
                agent_names.append(review.agent_name)

        # Deduplicate similar comments
        deduplicated_comments = self._deduplicate_comments(all_structured_comments)

        # Create combined summary
        combined_summary = self._create_combined_summary(all_summaries, agent_names)

        return FileReview(
            file_path=file_path,
            line_comments=all_line_comments,
            structured_comments=deduplicated_comments,
            summary=combined_summary,
            agent_name=", ".join(set(agent_names)) if agent_names else None,
        )

    def _deduplicate_comments(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """Remove duplicate or very similar comments."""
        if not comments:
            return []

        # Group comments by line number and category
        grouped_comments = defaultdict(list)
        for comment in comments:
            key = (comment.line_number, comment.category)
            grouped_comments[key].append(comment)

        deduplicated = []
        for (line_num, category), comment_group in grouped_comments.items():
            if len(comment_group) == 1:
                deduplicated.append(comment_group[0])
            else:
                # Merge similar comments
                merged_comment = self._merge_similar_comments(comment_group)
                deduplicated.append(merged_comment)

        # Sort by severity and line number
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        deduplicated.sort(key=lambda c: (severity_order.get(c.severity, 4), c.line_number))

        return deduplicated

    def _merge_similar_comments(self, comments: List[ReviewComment]) -> ReviewComment:
        """Merge similar comments from different agents."""
        if not comments:
            return None

        # Use the highest severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        highest_severity = min(comments, key=lambda c: severity_order.get(c.severity, 4))

        # Combine comments
        combined_comment = " | ".join([f"[{c.agent_name}]: {c.comment}" for c in comments])
        combined_agents = ", ".join(set(c.agent_name for c in comments))

        return ReviewComment(
            line_number=comments[0].line_number,
            comment=combined_comment,
            severity=highest_severity.severity,
            category=comments[0].category,
            agent_name=combined_agents,
        )

    def _create_combined_summary(self, summaries: List[str], agent_names: List[str]) -> str:
        """Create a combined summary from all agent summaries."""
        if not summaries:
            return "Multi-agent review completed"

        if len(summaries) == 1:
            return summaries[0]

        # Create a structured summary
        unique_agents = list(set(agent_names))
        summary_parts = [f"Multi-agent review completed by {', '.join(unique_agents)}:", ""]

        for i, summary in enumerate(summaries, 1):
            summary_parts.append(f"{i}. {summary}")

        return "\n".join(summary_parts)
