import boto3
import datetime as dt
from datetime import datetime

from ScrapyKeeper import config
from ScrapyKeeper.app import get_cluster_instances_ids
from ScrapyKeeper.app.util.config import get_instances_private_ips


def get_instance_memory_usage(app, instance_id):
    cw_conn = boto3.client('cloudwatch', region_name=app.config.get('AWS_DEFAULT_REGION'))

    response = cw_conn.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "myRequestToFindOutUsedMemory",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "CWAgent",
                        "MetricName": "mem_used_percent",
                        "Dimensions": [
                            {
                                "Name": "InstanceId",
                                "Value": instance_id
                            }
                        ]
                    },
                    "Period": 300,
                    "Stat": "Average"
                },
                "Label": "findOutUsedMemory",
                "ReturnData": True
            }
        ],
        StartTime=(datetime.utcnow() - dt.timedelta(minutes=5)),
        EndTime=(datetime.utcnow() - dt.timedelta(minutes=0))
    )

    metric_data_results = response.get('MetricDataResults')
    if 1 > len(metric_data_results):
        return None

    return metric_data_results.pop(0).get('Values').pop(0)


def cluster_has_enough_free_memory(app):
    if not config.RUNS_IN_CLOUD:
        return True

    instance_ids = get_cluster_instances_ids(app)
    instances_by_usage = {}
    for id in instance_ids:
        ips = get_instances_private_ips(app, [id])
        if len(ips) < 1:
            continue
        ip = ips.pop(0)
        instances_by_usage[ip] = get_instance_memory_usage(app, id)

    ip, memory = sorted(instances_by_usage.items(), key=lambda kv: kv[1] or 0).pop(0)

    if memory < config.USED_MEMORY_PERCENT_THRESHOLD:
        return True

    return False


