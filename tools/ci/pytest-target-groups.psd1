@{
    "pr-gui-shell" = @(
        "tests\test_gui_layout_core.py"
        "tests\test_gui_config_integration.py"
        "tests\test_gui_preset_manager.py"
        "tests\test_gui_state_binding.py"
        "tests\test_theme_consistency.py"
        "tests\test_theme_manager.py"
        "tests\test_visualization_theme.py"
    )
    "pr-stats" = @(
        "tests\test_gui_step5_interaction.py"
        "tests\test_anova_annotation_policy.py"
        "tests\test_plotly_charts.py"
        "tests\test_score_plot_label_modes.py"
        "tests\test_stats_matrix_routing.py"
    )
    "pr-runtime" = @(
        "tests\test_gui_runtime_feature_metadata.py"
        "tests\test_run_from_config_input_formats.py"
        "tests\test_sample_interface.py"
    )
    "repo-regression-core" = @(
        "tests\test_analysis_edgecases.py"
        "tests\test_app_config.py"
        "tests\test_config_load.py"
        "tests\test_core.py"
        "tests\test_dnp_import.py"
        "tests\test_ms_core_compat.py"
        "tests\test_paired_analysis.py"
        "tests\test_random_forest_njobs.py"
        "tests\test_run_from_config_input_formats.py"
        "tests\test_sample_interface.py"
        "tests\test_type_annotations.py"
    )
    "repo-regression-gui" = @(
        "tests\test_gui_layout_core.py"
        "tests\test_gui_config_integration.py"
        "tests\test_gui_preset_manager.py"
        "tests\test_gui_runtime_feature_metadata.py"
        "tests\test_gui_state_binding.py"
        "tests\test_plot_toolbar.py"
        "tests\test_theme_consistency.py"
        "tests\test_theme_manager.py"
        "tests\test_undo_redo.py"
        "tests\test_visualization_theme.py"
    )
    "repo-regression-stats" = @(
        "tests\test_anova_annotation_policy.py"
        "tests\test_gui_step5_interaction.py"
        "tests\test_plotly_charts.py"
        "tests\test_score_plot_label_modes.py"
        "tests\test_stats_matrix_routing.py"
    )
    "slow-gui" = @(
        "tests\test_gui_phase7_slow.py"
    )
    "compat-312" = @(
        "tests\test_config_load.py"
        "tests\test_core.py"
        "tests\test_paired_analysis.py"
        "tests\test_run_from_config_input_formats.py"
        "tests\test_sample_interface.py"
        "tests\test_plot_toolbar.py"
    )
}
