import { create } from "zustand";
import { persist } from "zustand/middleware";
import { socket } from "@/lib/websocket";
import { toast } from "@/components/ui";

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: "order" | "inventory" | "system";
  read: boolean;
  timestamp: string;
}

interface NotificationPreferences {
  order: boolean;
  inventory: boolean;
  system: boolean;
}

interface NotificationState {
  notifications: NotificationItem[];
  preferences: NotificationPreferences;
  addNotification: (title: string, message: string, category: NotificationItem["category"]) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
  updatePreference: (category: keyof NotificationPreferences, value: boolean) => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      notifications: [
        {
          id: "1",
          title: "Stock Alert",
          message: "SKU-TEST-001 has dropped below threshold level.",
          category: "inventory",
          read: false,
          timestamp: new Date().toISOString(),
        },
        {
          id: "2",
          title: "System Update",
          message: "Database failover recovery drill complete.",
          category: "system",
          read: true,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
        }
      ],
      preferences: {
        order: true,
        inventory: true,
        system: true,
      },

      addNotification: (title, message, category) => {
        const preferences = get().preferences;
        
        // Skip adding if preference for this category is disabled
        if (!preferences[category]) return;

        const newNotify: NotificationItem = {
          id: crypto.randomUUID(),
          title,
          message,
          category,
          read: false,
          timestamp: new Date().toISOString(),
        };

        set((state) => ({ notifications: [newNotify, ...state.notifications] }));

        // Optimistically display a toast notification
        let variant: "success" | "error" | "warning" | "info" = "info";
        if (category === "inventory") variant = "warning";
        else if (category === "order") variant = "success";
        
        toast(title, { description: message, variant });
      },

      markAsRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
        }));
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
        }));
      },

      clearAll: () => set({ notifications: [] }),

      updatePreference: (category, value) => {
        set((state) => ({
          preferences: { ...state.preferences, [category]: value }
        }));
      },
    }),
    {
      name: "cloudscale-notifications-store",
    }
  )
);

// Connect real-time socket events directly to the store actions
if (typeof window !== "undefined") {
  socket.subscribe((status, msg) => {
    if (status === "open" && msg && msg.type === "notification") {
      const { title, message, category } = msg.payload || {};
      if (title && message && category) {
        useNotificationStore.getState().addNotification(title, message, category);
      }
    }
  });
  
  // Connect to the WebSocket endpoint
  socket.connect();
}
