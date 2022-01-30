#!/usr/bin/python3
import sys, os
import inspect
import requests
import xmltodict
from kubernetes import dynamic, config
from kubernetes import client as k8s_client
from kubernetes.client import api_client

VERSION = "1"
TYPE = "xml"
API_KEY = os.environ.get("API_KEY", "")
DOMAIN = os.environ.get("DOMAIN", "")

K8S_CLIENT = None
CORE_API = None
NETWORK_API = None
CERT_API = None

def _kube_setup():
  global K8S_CLIENT
  global CORE_API
  global NETWORK_API
  global CERT_API

  if os.path.isdir("/var/run/secrets/kubernetes.io/serviceaccount"):
    k8s_config = config.load_incluster_config()
  else:
    k8s_config = config.load_kube_config()

  K8S_CLIENT = dynamic.DynamicClient(api_client.ApiClient(configuration=k8s_config))
  CERT_API = K8S_CLIENT.resources.get(
        api_version="cert-manager.io/v1", kind="Certificate"
    )

  CORE_API = k8s_client.CoreV1Api(api_client.ApiClient(k8s_config))
  NETWORK_API = k8s_client.NetworkingV1Api(api_client.ApiClient(k8s_config))


def _init():
  _kube_setup()


def get_services():
  services_response = CORE_API.list_service_for_all_namespaces()
  return services_response


def get_ingresses():
  ingress_response = NETWORK_API.list_ingress_for_all_namespaces()
  return ingress_response


def get_certificates():
  return CERT_API.get().attributes.items


def get_public_ip():
  ip = requests.get('https://api.ipify.org').content.decode('utf8')
  return ip


def list_dns_entries():
  OPERATION = "dnsListRecords"
  url = f"https://www.namesilo.com/api/{OPERATION}?version={VERSION}&type={TYPE}&key={API_KEY}&domain={DOMAIN}"

  return xmltodict.parse(requests.get(url).text)


def get_subdomain_entry(subdomain):
  entries = list_dns_entries()
  for entry in entries["namesilo"]["reply"]["resource_record"]:
    if entry["host"] == f"{subdomain}.{DOMAIN}":
      return entry
  return None


def update_dns_entry(id, hostname, value):
  url = f"https://www.namesilo.com/api/dnsUpdateRecord?version=1&type=xml&key={API_KEY}&domain={DOMAIN}&rrid={id}&rrhost={hostname}&rrvalue={value}&rrttl=7207"
  response = requests.get(url)
  print(f"Update dns entry response: {response.text}")
  return


def create_dns_entry(hostname, value, type):
  url = f"https://www.namesilo.com/api/dnsAddRecord?version=1&type=xml&key={API_KEY}&domain={DOMAIN}&rrtype={type}&rrhost={hostname}&rrvalue={value}&rrttl=7207"
  response = requests.get(url)
  print(f"Create dns entry response: {response.text}")
  return


def create_or_update_a_record(hostname, ip):
  entry = get_subdomain_entry(hostname)
  if entry:
    if entry["value"] != ip:
      print(f"Updating record. {hostname}.{DOMAIN} {ip}")
      update_dns_entry(hostname, ip, entry["record_id"])
    print(f"Record up-to-date. hostname={hostname} domain={DOMAIN}")
  else:
    print(f"Creating record {hostname}.{DOMAIN} {ip}")
    create_dns_entry(hostname, ip, "A")
  return


def create_or_update_cname_record(hostname, parent):
  if parent not in hostname:
    print(f"Will not create cname record. Not our domain. hostname={hostname} domain={parent}")
  else:
    subdomain_split_by_tld = hostname.split(DOMAIN)[0][0:-1]
    entry = get_subdomain_entry(hostname)
    if entry:
      print(f"Updating record {hostname} {parent} {subdomain_split_by_tld}")
      update_dns_entry(entry["record_id"], subdomain_split_by_tld, parent)
    else:
      print(f"Creating record {hostname} {parent} {subdomain_split_by_tld}")
      create_dns_entry(subdomain_split_by_tld, parent, "CNAME")
  return


def hook_main():
  public_ip = get_public_ip()
  create_or_update_a_record("902", public_ip)
  certs = get_certificates()
  for cert in certs:
    hostnames = cert["spec"]["dnsNames"]
    for hostname in hostnames:
      create_or_update_a_record(hostname.split(DOMAIN)[0][0:-1], public_ip)
  # TODO: get services, find cm-acme one, and change it to forwarded port on router


if __name__ == "__main__":
  if len(sys.argv) > 1 and sys.argv[1] == "--config":
      print(
          inspect.cleandoc(
              """
        ---
        configVersion: v1
        onStartup: 20
        settings:
          executionMinInterval: 30s
          executionBurst: 1
        kubernetes:
        - apiVersion: networking.k8s.io/v1
          kind: Ingress
          executeHookOnEvent: ["Added","Modified","Deleted"]
        schedule:
        - name: "every 5 min"
          crontab: "*/5 * * * *"
          allowFailure: true
      """
          )
      )
      exit()
  else:
      _init()
      hook_main()
