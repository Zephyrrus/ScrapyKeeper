import boto3
from requests import get
from requests.exceptions import ConnectionError


def get_cluster_servers(app):
    """
    Dynamically get the instance ips from a given cluster
    :return: list
    """
    ids = get_cluster_instances_ids(app)
    ips = get_instances_private_ips(app, ids)
    servers = ['http://{}:6800'.format(ip) for ip in ips]

    return servers


def get_cluster_instances_ids(app):
    ecs_conn = boto3.client('ecs', region_name=app.config.get('AWS_DEFAULT_REGION'))

    cluster_name = app.config.get('DEFAULT_CLUSTER_NAME')
    container_arns = ecs_conn.list_container_instances(cluster=cluster_name).get('containerInstanceArns', [])
    if not container_arns:
        return []

    detailed_containers = ecs_conn.describe_container_instances(cluster=cluster_name, containerInstances=container_arns)
    instance_ids = [c.get('ec2InstanceId') for c in detailed_containers.get('containerInstances', [])]
    if not instance_ids:
        return []

    return instance_ids


def get_instances_private_ips(app, instance_ids):
    ec2_conn = boto3.client('ec2', region_name=app.config.get('AWS_DEFAULT_REGION'))
    detailed_instances = ec2_conn.describe_instances(InstanceIds=instance_ids)

    ips = []
    for reservation in detailed_instances.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            ips.append(instance.get('PrivateIpAddress'))

    for ip in ips:
        scrapyd_url = 'http://{}:6800/daemonstatus.json'.format(ip)
        try:
            response = get(scrapyd_url)
            if '"status": "ok"' not in response.text:
                ips.remove(ip)
        except ConnectionError:
            ips.remove(ip)

    if not ips:
        return []

    return ips
