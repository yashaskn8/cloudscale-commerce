import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { AlertTriangle, RefreshCw, CheckCircle2 } from "lucide-react";
import { useNotificationStore } from "@/stores/notificationStore";
import { DataTable } from "@/components/data/DataTable";
import type { DataColumn } from "@/components/data/DataTable";
import { Badge, Button, Input, Modal, ModalFooter } from "@/components/ui";
import { useTranslation } from "@/i18n";

interface InventoryItem {
  id: string;
  sku: string;
  quantity: number;
  reserved: number;
}

export const Inventory: React.FC = () => {
  const { t } = useTranslation();
  const { addNotification } = useNotificationStore();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [restockQty, setRestockQty] = useState(10);
  const [updating, setUpdating] = useState(false);

  const fetchInventory = async () => {
    try {
      const res = await apiClient.get("/api/v1/inventory");
      setItems(res.data || []);
    } catch (err: any) {
      setError(t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const handleRestock = async () => {
    if (!selectedItem) return;
    setUpdating(true);
    try {
      await apiClient.post("/api/v1/inventory/restock", {
        sku: selectedItem.sku,
        quantity: restockQty,
      });

      addNotification("Stock Updated", `Successfully restocked SKU: ${selectedItem.sku} by ${restockQty}.`, "inventory");
      setSelectedItem(null);
      await fetchInventory();
    } catch (err: any) {
      alert("Failed to restock inventory item.");
    } finally {
      setUpdating(false);
    }
  };

  const columns: DataColumn<InventoryItem>[] = [
    {
      id: "sku",
      header: t("inventory.sku"),
      accessor: (row) => <span className="font-mono text-sm font-medium">{row.sku}</span>,
      sortAccessor: (row) => row.sku,
    },
    {
      id: "quantity",
      header: t("inventory.quantity"),
      accessor: (row) => <span className="font-semibold">{row.quantity}</span>,
      sortAccessor: (row) => row.quantity,
    },
    {
      id: "reserved",
      header: "Reserved Stock",
      accessor: (row) => <span className="text-muted-foreground">{row.reserved}</span>,
      sortAccessor: (row) => row.reserved,
    },
    {
      id: "status",
      header: t("inventory.status"),
      accessor: (row) => {
        const isLow = row.quantity <= 5;
        return isLow ? (
          <Badge variant="destructive" dot icon={<AlertTriangle className="h-3 w-3" />}>
            {t("inventory.lowStock")}
          </Badge>
        ) : (
          <Badge variant="success" dot icon={<CheckCircle2 className="h-3 w-3" />}>
            {t("inventory.inStock")}
          </Badge>
        );
      },
      sortAccessor: (row) => (row.quantity <= 5 ? 0 : 1),
    },
    {
      id: "actions",
      header: t("common.actions"),
      accessor: (row) => (
        <Button
          variant="outline"
          size="sm"
          icon={<RefreshCw className="h-3.5 w-3.5" />}
          onClick={() => setSelectedItem(row)}
        >
          {t("inventory.restock")}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{t("inventory.title")}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Monitor warehouse stock balances, item reservations, and low stock warnings
        </p>
      </div>

      {error ? (
        <div className="p-4 bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 rounded-lg">
          {error}
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          loading={loading}
          getRowId={(row) => row.id}
          emptyTitle="No inventory found"
          emptyDescription="Add products or update stock to view inventory"
          exportFilename="inventory-levels"
        />
      )}

      {/* Restock Dialog modal */}
      <Modal
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
        title={`Restock SKU: ${selectedItem?.sku || ""}`}
      >
        <div className="space-y-4">
          <Input
            type="number"
            label="Quantity to Add"
            value={restockQty}
            onChange={(e) => setRestockQty(parseInt(e.target.value))}
            required
          />
          <ModalFooter>
            <Button variant="outline" onClick={() => setSelectedItem(null)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleRestock} loading={updating}>
              {t("common.confirm")}
            </Button>
          </ModalFooter>
        </div>
      </Modal>
    </div>
  );
};

export default Inventory;

