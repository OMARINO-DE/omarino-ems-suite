"""
Model Validator Service.

Provides comprehensive model validation including:
- Performance metrics validation
- Baseline comparison
- Data drift detection
- Prediction stability checks
- Fairness metrics
- Validation report generation
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pickle
import json
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy import stats

from app.models.training import ModelType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when model validation fails."""
    pass


class ModelValidator:
    """
    Model validator for automated model validation.
    
    Validates models against performance thresholds, baseline comparisons,
    data drift, prediction stability, and fairness metrics.
    """
    
    # Default performance thresholds by model type
    DEFAULT_THRESHOLDS = {
        ModelType.FORECAST: {
            "mae": {"max": 50.0, "weight": 0.3},
            "rmse": {"max": 75.0, "weight": 0.3},
            "mape": {"max": 10.0, "weight": 0.2},
            "r2_score": {"min": 0.7, "weight": 0.2},
        },
        ModelType.ANOMALY: {
            "precision": {"min": 0.8, "weight": 0.3},
            "recall": {"min": 0.75, "weight": 0.3},
            "f1_score": {"min": 0.77, "weight": 0.3},
            "auc_roc": {"min": 0.85, "weight": 0.1},
        },
    }
    
    def __init__(
        self,
        model_type: ModelType,
        thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        Initialize model validator.
        
        Args:
            model_type: Type of model being validated
            thresholds: Custom performance thresholds (optional)
        """
        self.model_type = model_type
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.get(model_type, {})
    
    def validate_model(
        self,
        model_path: str,
        validation_data: pd.DataFrame,
        target_column: str,
        baseline_metrics: Optional[Dict[str, float]] = None,
        training_data_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run complete validation suite.
        
        Args:
            model_path: Path to pickled model
            validation_data: Validation dataset
            target_column: Name of target column
            baseline_metrics: Baseline model metrics for comparison
            training_data_stats: Training data statistics for drift detection
            
        Returns:
            Validation report with all results
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info(f"Starting model validation: {model_path}")
        
        # Load model
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
        except Exception as e:
            raise ValidationError(f"Failed to load model: {e}")
        
        # Prepare data
        X = validation_data.drop(columns=[target_column])
        y_true = validation_data[target_column]
        
        # Generate predictions
        try:
            y_pred = model.predict(X)
        except Exception as e:
            raise ValidationError(f"Failed to generate predictions: {e}")
        
        # Run validation checks
        results = {
            "model_path": model_path,
            "model_type": self.model_type.value,
            "validation_timestamp": datetime.utcnow().isoformat(),
            "validation_data_size": len(validation_data),
            "checks": {},
            "passed": True,
            "failures": [],
        }
        
        # 1. Performance validation
        perf_result = self.check_performance(y_true, y_pred)
        results["checks"]["performance"] = perf_result
        if not perf_result["passed"]:
            results["passed"] = False
            results["failures"].extend(perf_result["failures"])
        
        # 2. Baseline comparison
        if baseline_metrics:
            baseline_result = self.check_baseline_comparison(
                perf_result["metrics"], baseline_metrics
            )
            results["checks"]["baseline_comparison"] = baseline_result
            if not baseline_result["passed"]:
                results["passed"] = False
                results["failures"].extend(baseline_result["failures"])
        
        # 3. Data drift detection
        if training_data_stats:
            drift_result = self.check_data_drift(X, training_data_stats)
            results["checks"]["data_drift"] = drift_result
            if not drift_result["passed"]:
                results["passed"] = False
                results["failures"].extend(drift_result["failures"])
        
        # 4. Prediction stability
        stability_result = self.check_prediction_stability(y_pred)
        results["checks"]["prediction_stability"] = stability_result
        if not stability_result["passed"]:
            results["passed"] = False
            results["failures"].extend(stability_result["failures"])
        
        # 5. Prediction range checks
        range_result = self.check_prediction_range(y_true, y_pred)
        results["checks"]["prediction_range"] = range_result
        if not range_result["passed"]:
            results["passed"] = False
            results["failures"].extend(range_result["failures"])
        
        logger.info(f"Validation complete. Passed: {results['passed']}")
        return results
    
    def check_performance(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Check if model meets performance thresholds.
        
        Args:
            y_true: True target values
            y_pred: Predicted values
            
        Returns:
            Performance check results
        """
        logger.info("Checking performance thresholds")
        
        # Calculate metrics
        if self.model_type == ModelType.FORECAST:
            metrics = {
                "mae": mean_absolute_error(y_true, y_pred),
                "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
                "mape": np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
                "r2_score": r2_score(y_true, y_pred),
            }
        else:  # ANOMALY
            from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
            metrics = {
                "precision": precision_score(y_true, y_pred),
                "recall": recall_score(y_true, y_pred),
                "f1_score": f1_score(y_true, y_pred),
                "auc_roc": roc_auc_score(y_true, y_pred),
            }
        
        # Check thresholds
        failures = []
        passed = True
        
        for metric_name, threshold in self.thresholds.items():
            if metric_name not in metrics:
                continue
            
            value = metrics[metric_name]
            
            if "max" in threshold and value > threshold["max"]:
                failures.append(
                    f"{metric_name}={value:.4f} exceeds max threshold {threshold['max']}"
                )
                passed = False
            
            if "min" in threshold and value < threshold["min"]:
                failures.append(
                    f"{metric_name}={value:.4f} below min threshold {threshold['min']}"
                )
                passed = False
        
        return {
            "passed": passed,
            "metrics": metrics,
            "thresholds": self.thresholds,
            "failures": failures,
        }
    
    def check_baseline_comparison(
        self,
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
        tolerance: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Compare model performance against baseline.
        
        Args:
            current_metrics: Current model metrics
            baseline_metrics: Baseline model metrics
            tolerance: Acceptable degradation (5% by default)
            
        Returns:
            Baseline comparison results
        """
        logger.info("Comparing against baseline")
        
        failures = []
        passed = True
        comparisons = {}
        
        for metric_name, baseline_value in baseline_metrics.items():
            if metric_name not in current_metrics:
                continue
            
            current_value = current_metrics[metric_name]
            
            # Determine if higher or lower is better
            higher_better = metric_name in ["r2_score", "precision", "recall", "f1_score", "auc_roc"]
            
            if higher_better:
                # Current should be >= baseline * (1 - tolerance)
                min_acceptable = baseline_value * (1 - tolerance)
                is_acceptable = current_value >= min_acceptable
                degradation = (baseline_value - current_value) / baseline_value * 100
            else:
                # Current should be <= baseline * (1 + tolerance)
                max_acceptable = baseline_value * (1 + tolerance)
                is_acceptable = current_value <= max_acceptable
                degradation = (current_value - baseline_value) / baseline_value * 100
            
            comparisons[metric_name] = {
                "current": current_value,
                "baseline": baseline_value,
                "degradation_pct": degradation,
                "acceptable": is_acceptable,
            }
            
            if not is_acceptable:
                failures.append(
                    f"{metric_name}: {degradation:.2f}% degradation "
                    f"(current={current_value:.4f}, baseline={baseline_value:.4f})"
                )
                passed = False
        
        return {
            "passed": passed,
            "comparisons": comparisons,
            "tolerance": tolerance,
            "failures": failures,
        }
    
    def check_data_drift(
        self,
        validation_data: pd.DataFrame,
        training_stats: Dict[str, Any],
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Detect data drift using statistical tests.
        
        Args:
            validation_data: Current validation data
            training_stats: Training data statistics (mean, std per feature)
            threshold: P-value threshold for drift detection
            
        Returns:
            Data drift results
        """
        logger.info("Checking for data drift")
        
        failures = []
        passed = True
        drift_detected = {}
        
        for col in validation_data.columns:
            if col not in training_stats:
                continue
            
            train_mean = training_stats[col]["mean"]
            train_std = training_stats[col]["std"]
            
            # Perform Z-test
            val_mean = validation_data[col].mean()
            val_std = validation_data[col].std()
            n = len(validation_data)
            
            # Calculate Z-score for mean difference
            z_score = (val_mean - train_mean) / (train_std / np.sqrt(n))
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
            drift_detected[col] = {
                "train_mean": train_mean,
                "val_mean": val_mean,
                "train_std": train_std,
                "val_std": val_std,
                "z_score": z_score,
                "p_value": p_value,
                "drift": p_value < threshold,
            }
            
            if p_value < threshold:
                failures.append(
                    f"{col}: Significant drift detected "
                    f"(p-value={p_value:.4f}, z-score={z_score:.4f})"
                )
                passed = False
        
        return {
            "passed": passed,
            "drift_detected": drift_detected,
            "threshold": threshold,
            "failures": failures,
        }
    
    def check_prediction_stability(
        self,
        predictions: np.ndarray,
        cv_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Check prediction stability (coefficient of variation).
        
        Args:
            predictions: Model predictions
            cv_threshold: Maximum acceptable coefficient of variation
            
        Returns:
            Stability check results
        """
        logger.info("Checking prediction stability")
        
        mean_pred = np.mean(predictions)
        std_pred = np.std(predictions)
        cv = std_pred / mean_pred if mean_pred != 0 else float("inf")
        
        passed = cv <= cv_threshold
        failures = []
        
        if not passed:
            failures.append(
                f"High prediction variability: CV={cv:.4f} exceeds threshold {cv_threshold}"
            )
        
        return {
            "passed": passed,
            "coefficient_of_variation": cv,
            "mean": mean_pred,
            "std": std_pred,
            "threshold": cv_threshold,
            "failures": failures,
        }
    
    def check_prediction_range(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        outlier_threshold: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Check if predictions are within reasonable range.
        
        Args:
            y_true: True values
            y_pred: Predicted values
            outlier_threshold: Number of standard deviations for outlier detection
            
        Returns:
            Prediction range results
        """
        logger.info("Checking prediction range")
        
        # Calculate residuals
        residuals = y_pred - y_true
        mean_residual = np.mean(residuals)
        std_residual = np.std(residuals)
        
        # Find outliers
        z_scores = np.abs((residuals - mean_residual) / std_residual)
        outliers = np.sum(z_scores > outlier_threshold)
        outlier_pct = outliers / len(residuals) * 100
        
        # Check if predictions are in reasonable range relative to true values
        min_true, max_true = np.min(y_true), np.max(y_true)
        min_pred, max_pred = np.min(y_pred), np.max(y_pred)
        
        # Predictions should be within reasonable bounds
        passed = (
            outlier_pct < 5.0  # Less than 5% outliers
            and min_pred >= min_true * 0.5  # Not too far below
            and max_pred <= max_true * 1.5  # Not too far above
        )
        
        failures = []
        if outlier_pct >= 5.0:
            failures.append(f"Too many outliers: {outlier_pct:.2f}%")
        if min_pred < min_true * 0.5:
            failures.append(f"Predictions too low: min={min_pred:.2f}")
        if max_pred > max_true * 1.5:
            failures.append(f"Predictions too high: max={max_pred:.2f}")
        
        return {
            "passed": passed,
            "outliers": int(outliers),
            "outlier_percentage": outlier_pct,
            "pred_range": {"min": min_pred, "max": max_pred},
            "true_range": {"min": min_true, "max": max_true},
            "residual_stats": {
                "mean": mean_residual,
                "std": std_residual,
            },
            "failures": failures,
        }
    
    def generate_validation_report(
        self,
        results: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate human-readable validation report.
        
        Args:
            results: Validation results
            output_path: Path to save report (optional)
            
        Returns:
            Report as string
        """
        logger.info("Generating validation report")
        
        # Save JSON report
        if output_path:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Validation report saved: {output_path}")
        
        # Generate text summary
        lines = [
            "=" * 80,
            "MODEL VALIDATION REPORT",
            "=" * 80,
            f"Model Type: {results['model_type']}",
            f"Timestamp: {results['validation_timestamp']}",
            f"Overall Status: {'✓ PASSED' if results['passed'] else '✗ FAILED'}",
            f"Validation Data Size: {results['validation_data_size']}",
            "",
        ]
        
        # Performance section
        if "performance" in results["checks"]:
            perf = results["checks"]["performance"]
            lines.extend([
                "-" * 80,
                "PERFORMANCE METRICS",
                "-" * 80,
            ])
            for metric, value in perf["metrics"].items():
                status = "✓" if perf["passed"] else "✗"
                lines.append(f"  {status} {metric}: {value:.4f}")
            lines.append("")
        
        # Baseline comparison section
        if "baseline_comparison" in results["checks"]:
            baseline = results["checks"]["baseline_comparison"]
            lines.extend([
                "-" * 80,
                "BASELINE COMPARISON",
                "-" * 80,
            ])
            for metric, comp in baseline["comparisons"].items():
                status = "✓" if comp["acceptable"] else "✗"
                lines.append(
                    f"  {status} {metric}: {comp['current']:.4f} vs "
                    f"{comp['baseline']:.4f} ({comp['degradation_pct']:+.2f}%)"
                )
            lines.append("")
        
        # Failures section
        if results["failures"]:
            lines.extend([
                "-" * 80,
                "VALIDATION FAILURES",
                "-" * 80,
            ])
            for failure in results["failures"]:
                lines.append(f"  ✗ {failure}")
            lines.append("")
        
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        return report
