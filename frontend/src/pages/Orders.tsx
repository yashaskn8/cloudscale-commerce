import React, { useEffect, useState, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { useTranslation } from "@/i18n";
import { DataTable } from "@/components/data/DataTable";
import type { DataColumn } from "@/components/data/DataTable";
import { Badge, PageHeader, Button, Alert } from "@/components/ui";
import { formatCurrency, formatDate } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

interface Order {
  id: string;
  status: string;
  total_amount: number;
  created_at: string;
}

export const Orders: React.FC = () => {
  const { t } = useTranslation();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.get("/api/v1/orders");
      setOrders(res.data || []);
    } catch {
      setError(t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const columns: DataColumn<Order>[] = [
    {
      id: "id",
      header: t("orders.orderId"),
      accessor: (row) => <span className="font-mono text-sm font-medium">{row.id}</span>,
      sortAccessor: (row) => row.id,
    },
    {
      id: "created_at",
      header: t("orders.date"),
      accessor: (row) => <span>{formatDate(row.created_at)}</span>,
      sortAccessor: (row) => row.created_at,
    },
    {
      id: "status",
      header: t("orders.status"),
      accessor: (row) => {
        const status = row.status.toLowerCase();
        let variant: "success" | "warning" | "destructive" | "info" = "info";
        if (status === "success" || status === "completed") variant = "success";
        else if (status === "pending" || status === "processing") variant = "warning";
        else if (status === "failed") variant = "destructive";

        return (
          <Badge variant={variant} dot className="uppercase">
            {t(`orders.${status}` as any) || row.status}
          </Badge>
        );
      },
      sortAccessor: (row) => row.status,
    },
    {
      id: "amount",
      header: t("orders.amount"),
      accessor: (row) => <span className="font-semibold">{formatCurrency(row.total_amount)}</span>,
      sortAccessor: (row) => row.total_amount,
      align: "right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("orders.title")}
        subtitle="Review details of your transactions and checkout saga states"
        actions={
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />}
            onClick={fetchOrders}
          >
            Refresh
          </Button>
        }
      />

      {error ? (
        <Alert variant="error">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchOrders}>
              Retry
            </Button>
          </div>
        </Alert>
      ) : (
        <DataTable
          columns={columns}
          data={orders}
          loading={loading}
          getRowId={(row) => row.id}
          emptyTitle={t("orders.noOrders")}
          emptyDescription={t("cart.emptyDescription")}
          exportFilename="orders-history"
        />
      )}
    </div>
  );
};

export default Orders;
