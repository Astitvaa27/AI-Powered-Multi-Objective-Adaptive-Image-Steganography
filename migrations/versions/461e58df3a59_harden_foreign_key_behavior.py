"""harden foreign key behavior"""

from typing import Sequence, Union

from alembic import op

# revision identifiers
revision = "461e58df3a59"
down_revision = "c6853b122b05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Optional relationships → SET NULL

    op.drop_constraint("images_owner_id_fkey", "images", type_="foreignkey")
    op.create_foreign_key(
        "images_owner_id_fkey",
        "images",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_user_id_fkey",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Historical / research relationships → RESTRICT

    restrict_constraints = [
        ("users_role_id_fkey", "users", "roles", "role_id"),
        ("user_profiles_user_id_fkey", "user_profiles", "users", "user_id"),
        (
            "embedding_configurations_method_id_fkey",
            "embedding_configurations",
            "embedding_methods",
            "method_id",
        ),
        (
            "steganography_sessions_configuration_id_fkey",
            "steganography_sessions",
            "embedding_configurations",
            "configuration_id",
        ),
        (
            "steganography_sessions_cover_image_id_fkey",
            "steganography_sessions",
            "images",
            "cover_image_id",
        ),
        (
            "steganography_sessions_payload_id_fkey",
            "steganography_sessions",
            "payloads",
            "payload_id",
        ),
        (
            "steganography_sessions_stego_image_id_fkey",
            "steganography_sessions",
            "images",
            "stego_image_id",
        ),
        (
            "steganography_sessions_user_id_fkey",
            "steganography_sessions",
            "users",
            "user_id",
        ),
        (
            "embedding_regions_session_id_fkey",
            "embedding_regions",
            "steganography_sessions",
            "session_id",
        ),
        (
            "extraction_records_session_id_fkey",
            "extraction_records",
            "steganography_sessions",
            "session_id",
        ),
        (
            "analysis_sessions_image_id_fkey",
            "analysis_sessions",
            "images",
            "image_id",
        ),
        (
            "analysis_sessions_user_id_fkey",
            "analysis_sessions",
            "users",
            "user_id",
        ),
        (
            "analysis_reports_analysis_session_id_fkey",
            "analysis_reports",
            "analysis_sessions",
            "analysis_session_id",
        ),
        (
            "model_predictions_analysis_session_id_fkey",
            "model_predictions",
            "analysis_sessions",
            "analysis_session_id",
        ),
        (
            "model_predictions_model_version_id_fkey",
            "model_predictions",
            "model_versions",
            "model_version_id",
        ),
        (
            "suspicious_regions_analysis_session_id_fkey",
            "suspicious_regions",
            "analysis_sessions",
            "analysis_session_id",
        ),
        (
            "optimization_runs_image_id_fkey",
            "optimization_runs",
            "images",
            "image_id",
        ),
        (
            "optimization_runs_payload_id_fkey",
            "optimization_runs",
            "payloads",
            "payload_id",
        ),
        (
            "optimization_runs_user_id_fkey",
            "optimization_runs",
            "users",
            "user_id",
        ),
        (
            "optimization_iterations_optimization_run_id_fkey",
            "optimization_iterations",
            "optimization_runs",
            "optimization_run_id",
        ),
        (
            "candidate_configurations_iteration_id_fkey",
            "candidate_configurations",
            "optimization_iterations",
            "iteration_id",
        ),
        (
            "candidate_configurations_method_id_fkey",
            "candidate_configurations",
            "embedding_methods",
            "method_id",
        ),
        (
            "objective_scores_candidate_configuration_id_fkey",
            "objective_scores",
            "candidate_configurations",
            "candidate_configuration_id",
        ),
        (
            "model_evaluations_dataset_id_fkey",
            "model_evaluations",
            "datasets",
            "dataset_id",
        ),
        (
            "model_evaluations_model_version_id_fkey",
            "model_evaluations",
            "model_versions",
            "model_version_id",
        ),
        (
            "training_runs_dataset_id_fkey",
            "training_runs",
            "datasets",
            "dataset_id",
        ),
        (
            "training_runs_model_version_id_fkey",
            "training_runs",
            "model_versions",
            "model_version_id",
        ),
        (
            "dataset_images_dataset_id_fkey",
            "dataset_images",
            "datasets",
            "dataset_id",
        ),
        (
            "dataset_images_image_id_fkey",
            "dataset_images",
            "images",
            "image_id",
        ),
        (
            "experiments_user_id_fkey",
            "experiments",
            "users",
            "user_id",
        ),
        (
            "experiment_runs_experiment_id_fkey",
            "experiment_runs",
            "experiments",
            "experiment_id",
        ),
        (
            "experiment_results_experiment_run_id_fkey",
            "experiment_results",
            "experiment_runs",
            "experiment_run_id",
        ),
        (
            "experiment_results_image_id_fkey",
            "experiment_results",
            "images",
            "image_id",
        ),
        (
            "experiment_results_method_id_fkey",
            "experiment_results",
            "embedding_methods",
            "method_id",
        ),
    ]

    for name, table, ref_table, column in restrict_constraints:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            ref_table,
            [column],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for FK hardening migration.")