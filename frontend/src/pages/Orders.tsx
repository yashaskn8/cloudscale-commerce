import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useTranslation } from "@/i18n";
import { DataTable } from "@/components/data/DataTable";
import type { DataColumn } from "@/components/data/DataTable";
import { Badge } from "@/components/ui";
import { formatCurrency, formatDate } from "@/lib/utils";

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

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const res = await apiClient.get("/api/v1/orders");
        setOrders(res.data || []);
      } catch (err: any) {
        setError(t("common.error"));
      } finally {
        setLoading(false);
      }
    };
    fetchOrders();
  }, [t]);

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
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{t("orders.title")}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Review details of your transactions and checkout saga states
        </p>
      </div>

      {error ? (
        <div className="p-4 bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 rounded-lg">
          {error}
        </div>
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

