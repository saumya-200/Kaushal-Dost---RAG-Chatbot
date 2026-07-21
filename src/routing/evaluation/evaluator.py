import time
import json
import logging
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)

class Evaluator:
    """
    Evaluates the RAG router accuracy and performance metrics on a given dataset.
    Generates structured reports including Persona, Intent, and Template accuracy,
    P95/average latencies, routing distribution, and confusion matrices.
    """
    def __init__(self, router):
        self.router = router

    async def evaluate_dataset(self, dataset: list[dict]) -> dict:
        """
        Runs evaluation on a dataset list of dicts.
        Each test item should look like:
        {
            "query": "What is the SPMU helpline?",
            "expected_persona": "General Public",
            "expected_intent": "Helpline",
            "expected_stage": "greeting" / "static_lookup" / "faiss_direct" / "out_of_scope" / "fallback"
        }
        """
        results = []
        latencies = []
        
        # True vs Predicted classifications
        persona_y_true = []
        persona_y_pred = []
        
        intent_y_true = []
        intent_y_pred = []
        
        stage_y_true = []
        stage_y_pred = []
        
        false_positives_template = 0
        false_negatives_template = 0
        
        logger.info(f"Starting evaluation on {len(dataset)} items...")
        
        for idx, item in enumerate(dataset):
            query = item["query"]
            expected_p = item.get("expected_persona", "Unknown")
            expected_i = item.get("expected_intent", "General")
            expected_s = item.get("expected_stage", "fallback")
            
            t0 = time.time()
            stage, answer, meta = await self.router.route(query)
            latency = (time.time() - t0) * 1000
            
            latencies.append(latency)
            
            pred_p = meta.get("detected_persona", "Unknown")
            pred_i = meta.get("detected_intent", "General")
            
            results.append({
                "query": query,
                "expected": {"persona": expected_p, "intent": expected_i, "stage": expected_s},
                "predicted": {"persona": pred_p, "intent": pred_i, "stage": stage},
                "latency_ms": latency,
                "answer": answer
            })
            
            persona_y_true.append(expected_p)
            persona_y_pred.append(pred_p)
            
            intent_y_true.append(expected_i)
            intent_y_pred.append(pred_i)
            
            stage_y_true.append(expected_s)
            stage_y_pred.append(stage)
            
            # Analyze Template False Positives / False Negatives
            # False Positive: predicted static_lookup/template but expected fallback/out_of_scope
            if stage in ("static_lookup", "template") and expected_s not in ("static_lookup", "template"):
                false_positives_template += 1
            # False Negative: predicted fallback/out_of_scope but expected static_lookup/template
            elif stage not in ("static_lookup", "template") and expected_s in ("static_lookup", "template"):
                false_negatives_template += 1

        # Accuracy Calculations
        persona_acc = sum(1 for t, p in zip(persona_y_true, persona_y_pred) if t == p) / len(dataset)
        intent_acc = sum(1 for t, p in zip(intent_y_true, intent_y_pred) if t == p) / len(dataset)
        stage_acc = sum(1 for t, p in zip(stage_y_true, stage_y_pred) if t == p) / len(dataset)
        
        # Calculate Latencies
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        
        # Routing distribution
        dist = defaultdict(int)
        for r in results:
            dist[r["predicted"]["stage"]] += 1
        distribution = {k: v / len(dataset) for k, v in dist.items()}
        
        # Compute Confusion Matrices (as dictionary mapping)
        def get_confusion_matrix(y_true, y_pred):
            cm = defaultdict(lambda: defaultdict(int))
            for t, p in zip(y_true, y_pred):
                cm[t][p] += 1
            return {k: dict(v) for k, v in cm.items()}

        persona_cm = get_confusion_matrix(persona_y_true, persona_y_pred)
        intent_cm = get_confusion_matrix(intent_y_true, intent_y_pred)
        
        # Separate Stage Accuracy Metrics
        def filter_accuracy(stage_name):
            true_filter = [t for t, s in zip(stage_y_true, stage_y_true) if s == stage_name]
            pred_filter = [p for t, p in zip(stage_y_true, stage_y_pred) if t == stage_name]
            if not true_filter:
                return 1.0
            return sum(1 for t, p in zip(true_filter, pred_filter) if t == p) / len(true_filter)
            
        report = {
            "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_items_evaluated": len(dataset),
            "accuracies": {
                "persona_accuracy": round(persona_acc, 4),
                "intent_accuracy": round(intent_acc, 4),
                "overall_stage_accuracy": round(stage_acc, 4),
                "greeting_accuracy": round(filter_accuracy("greeting"), 4),
                "static_lookup_accuracy": round(filter_accuracy("static_lookup"), 4),
                "out_of_scope_accuracy": round(filter_accuracy("out_of_scope"), 4),
                "fallback_accuracy": round(filter_accuracy("fallback"), 4),
                "faiss_direct_accuracy": round(filter_accuracy("faiss_direct"), 4)
            },
            "performance": {
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2)
            },
            "routing_distribution": distribution,
            "template_error_rates": {
                "false_positives": false_positives_template,
                "false_negatives": false_negatives_template
            },
            "confusion_matrices": {
                "persona": persona_cm,
                "intent": intent_cm
            },
            "details": results
        }
        
        return report
