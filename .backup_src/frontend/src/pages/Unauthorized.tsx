import { Link } from "react-router";
import { ShieldAlert } from "lucide-react";

export const Unauthorized: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <div className="p-4 bg-red-50 dark:bg-red-950/20 rounded-2xl mb-4 text-red-500">
        <ShieldAlert className="h-12 w-12" />
      </div>
      <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-2">
        Access Denied
      </h1>
      <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
        You do not possess the required RBAC permissions to access this page. Please contact your administrator.
      </p>
      <Link
        to="/"
        className="px-5 py-2.5 bg-primary text-white font-semibold rounded-lg shadow-sm hover:bg-primary/95"
      >
        Go Home
      </Link>
    </div>
  );
};
export default Unauthorized;
