# Signal tenancy for Red Hat OpenShift ServiceMesh

Signals (metrics/prometheus, logs/loki, traces/tempo) in multi-tenancy environments are more complex to separate in particular when looking at is component "x" considered as tenancy component or a shared on (like an Ingress Gateway). Be ware that in particular traces might carry more information of none tenant systems (like an ingress) that logs and metrics do not. On the other hand does it help to see only a part or are you interested in tracing the complete path from client down to the bit being written in some storage backend ? 

## Preparing ServiceMesh for multi-tenancy signal configuration 

There are multiple parts we need to configure for such use-case:

* the pilot (Istio) needs to provide the `extensionProviders` for each tenant 
* the signal collector need to be separated for each tenant
* the signal storage (prometheus,tempo,loki) need to be separated for each tenant
* shared resources need to go to all tenants or none (if not considered being part of tenancy)

The first that will hit you is resource consumption of the signal stores. Each component requires typically a lot of resources to ensure reliability and high availability. Prometheus uses shards to duplicate data for HA, tempo and loki use multiple ingestors for that and a S3 Bucket which would also need to be per tenant of course.

So, if resource consumption isn't stopping you here are the steps to get tenancy based signal handling Red Hat OpenShift ServiceMesh.

**NOTE** Setting up each signal storage is out of scope of this repository

## Istio CR the pilot configuration

`extensionsProviders` are defined as; extension providers that extend Istio’s functionality. That means using `opentelemetry` for tracing and `envoyOtelAls` for logs as example.

Such extensions are configured in the Istio CR under `spec.values.meshConfig.extensionProviders` and look like

```
- name: default
  opentelemetry:
    port: 4317
    service: otel-collector.istio-system.svc.cluster.local
```

They can be added up to a limit of `maxItems: 1000` according to the CRD. This means we can add up to 1000 tenants for signals if no other extensions are required.

The repo provides an `istio.yml` which configured 3 tenants for traces and logs.

## The collector for our signals

Even though Istio provides the flexibilty to adjust the samplingRate (consideration how much tracing data should be collected) it lacks the same for other signals like metrics and logs. The OpenTelemetryCollector (otc) can be used to extend that limitation beside the flexibility to do tons of other stuff to the signals received. 
In the repository scope, we'll also see how the otc will use the `targetAllocator` to receive the tenant based services to scrape for metrics.

The otc configuration for each tenant will do exactly the same:

* receive grpc/http OTEL signals for traces and logs
* receive a list of Service/PodMonitor endpoints to scrape from the targetAllocator
* enforce a tenant label/attribute to the signals
* duplicate the metrics signal to each shard 
* queue signals to disk in case of storage outage 

## The targetAllocator for dynamic Service/PodMonitor discovery

the targetAllocator from the OpenTelemetry Suite requires access to the KubeAPI to retrieve objects for it's tenant namespaces (Service/PodMonitor,endpoints). It will distribute and split the list of received targets to the available otc collectors (sharing load of scrapes by splitting it to multiple collectors).

## Tenant namespace enforced signal configuration

Istio provides a `telemetry` CR to configure mesh-wide or namespace based which signal should be handled by which extension. **NOTE** the Telemetry CR also provides `selector` attributes to even grant in-namespace separation. This selector isn't reliable in particular when multiple Telemetry CR's are present as first-come, first-serve will create a weird behavior in case of overlaps and writing one larget telemetry CR is way more uncofortable than using an otc collector logic (beside being far more flexible with otc).

# Conclusion

Even though this repository provides all necessary CR's to deploy multi-tenancy signal handling, it requires quite a lot of infrastructure for you to reproduce. The best way to achieve multi-tenancy signal handling without investing a ton is to set all otc service.exporters to `debug` which will just output the received or processed signals to the collector stdout.
