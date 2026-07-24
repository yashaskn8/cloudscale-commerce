import { Outlet } from "react-router";
import { ShoppingBag } from "lucide-react";

export const GuestLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      <div className="w-full max-w-md bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700">
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-primary/10 rounded-2xl mb-3">
            <ShoppingBag className="h-10 w-10 text-primary" />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 dark:text-white">
            CloudScale Commerce
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Enterprise Cloud-Native Platform
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
};
