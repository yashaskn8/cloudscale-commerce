# ==============================================================================
# Root Outputs
# ==============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_id
}

output "rds_primary_endpoint" {
  description = "RDS primary writer endpoint"
  value       = module.rds.primary_endpoint
}

output "rds_reader_endpoint" {
  description = "RDS reader endpoint"
  value       = module.rds.reader_endpoint
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.elasticache.primary_endpoint
}

output "msk_bootstrap_brokers" {
  description = "MSK Kafka bootstrap broker connection string"
  value       = module.msk.bootstrap_brokers_tls
}

output "s3_backups_bucket" {
  description = "S3 bucket for database backups"
  value       = module.s3.backups_bucket_id
}
