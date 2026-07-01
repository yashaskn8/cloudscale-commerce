{{/*
CloudScale Commerce — Shared Helm Template Helpers.
Used by all sub-charts for consistent naming, labeling, and selector conventions.
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "cloudscale.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "cloudscale.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Standard Kubernetes labels.
*/}}
{{- define "cloudscale.labels" -}}
helm.sh/chart: {{ include "cloudscale.name" . }}
app.kubernetes.io/name: {{ include "cloudscale.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: cloudscale-commerce
{{- end }}

{{/*
Selector labels (used in matchLabels).
*/}}
{{- define "cloudscale.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudscale.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "cloudscale.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "cloudscale.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
