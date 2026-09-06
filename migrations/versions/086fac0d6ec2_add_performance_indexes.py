"""add performance indexes

Revision ID: 086fac0d6ec2
Revises: 483ef07fc332
Create Date: 2026-08-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "086fac0d6ec2"
down_revision: Union[str, Sequence[str], None] = "483ef07fc332"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for frequently queried foreign-key columns."""
    op.create_index("ix_analysis_reports_analysis_session_id", "analysis_reports", ["analysis_session_id"], unique=False)
    op.create_index("ix_analysis_sessions_image_id", "analysis_sessions", ["image_id"], unique=False)
    op.create_index("ix_analysis_sessions_user_id", "analysis_sessions", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_candidate_configurations_method_id", "candidate_configurations", ["method_id"], unique=False)
    op.create_index("ix_dataset_images_dataset_id", "dataset_images", ["dataset_id"], unique=False)
    op.create_index("ix_dataset_images_image_id", "dataset_images", ["image_id"], unique=False)
    op.create_index("ix_experiment_results_experiment_run_id", "experiment_results", ["experiment_run_id"], unique=False)
    op.create_index("ix_experiment_results_image_id", "experiment_results", ["image_id"], unique=False)
    op.create_index("ix_experiment_results_method_id", "experiment_results", ["method_id"], unique=False)
    op.create_index("ix_experiment_runs_experiment_id", "experiment_runs", ["experiment_id"], unique=False)
    op.create_index("ix_experiments_user_id", "experiments", ["user_id"], unique=False)
    op.create_index("ix_extraction_records_session_id", "extraction_records", ["session_id"], unique=False)
    op.create_index("ix_images_owner_id", "images", ["owner_id"], unique=False)
    op.create_index("ix_model_evaluations_model_version_id", "model_evaluations", ["model_version_id"], unique=False)
    op.create_index("ix_model_evaluations_dataset_id", "model_evaluations", ["dataset_id"], unique=False)
    op.create_index("ix_model_predictions_analysis_session_id", "model_predictions", ["analysis_session_id"], unique=False)
    op.create_index("ix_model_predictions_model_version_id", "model_predictions", ["model_version_id"], unique=False)
    op.create_index("ix_objective_scores_candidate_configuration_id", "objective_scores", ["candidate_configuration_id"], unique=False)
    op.create_index("ix_optimization_iterations_optimization_run_id", "optimization_iterations", ["optimization_run_id"], unique=False)
    op.create_index("ix_optimization_runs_user_id", "optimization_runs", ["user_id"], unique=False)
    op.create_index("ix_optimization_runs_image_id", "optimization_runs", ["image_id"], unique=False)
    op.create_index("ix_optimization_runs_payload_id", "optimization_runs", ["payload_id"], unique=False)
    op.create_index("ix_steganography_sessions_cover_image_id", "steganography_sessions", ["cover_image_id"], unique=False)
    op.create_index("ix_steganography_sessions_user_id", "steganography_sessions", ["user_id"], unique=False)
    op.create_index("ix_suspicious_regions_analysis_session_id", "suspicious_regions", ["analysis_session_id"], unique=False)
    op.create_index("ix_training_runs_dataset_id", "training_runs", ["dataset_id"], unique=False)
    op.create_index("ix_training_runs_model_version_id", "training_runs", ["model_version_id"], unique=False)



def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index("ix_training_runs_model_version_id", table_name="training_runs")
    op.drop_index("ix_training_runs_dataset_id", table_name="training_runs")
    op.drop_index("ix_suspicious_regions_analysis_session_id", table_name="suspicious_regions")
    op.drop_index("ix_steganography_sessions_user_id", table_name="steganography_sessions")
    op.drop_index("ix_steganography_sessions_cover_image_id", table_name="steganography_sessions")
    op.drop_index("ix_optimization_runs_payload_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_image_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_user_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_iterations_optimization_run_id", table_name="optimization_iterations")
    op.drop_index("ix_objective_scores_candidate_configuration_id", table_name="objective_scores")
    op.drop_index("ix_model_predictions_model_version_id", table_name="model_predictions")
    op.drop_index("ix_model_predictions_analysis_session_id", table_name="model_predictions")
    op.drop_index("ix_model_evaluations_dataset_id", table_name="model_evaluations")
    op.drop_index("ix_model_evaluations_model_version_id", table_name="model_evaluations")
    op.drop_index("ix_images_owner_id", table_name="images")
    op.drop_index("ix_extraction_records_session_id", table_name="extraction_records")
    op.drop_index("ix_experiments_user_id", table_name="experiments")
    op.drop_index("ix_experiment_runs_experiment_id", table_name="experiment_runs")
    op.drop_index("ix_experiment_results_method_id", table_name="experiment_results")
    op.drop_index("ix_experiment_results_image_id", table_name="experiment_results")
    op.drop_index("ix_experiment_results_experiment_run_id", table_name="experiment_results")
    op.drop_index("ix_dataset_images_image_id", table_name="dataset_images")
    op.drop_index("ix_dataset_images_dataset_id", table_name="dataset_images")
    op.drop_index("ix_candidate_configurations_method_id", table_name="candidate_configurations")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_analysis_sessions_user_id", table_name="analysis_sessions")
    op.drop_index("ix_analysis_sessions_image_id", table_name="analysis_sessions")
    op.drop_index("ix_analysis_reports_analysis_session_id", table_name="analysis_reports")
