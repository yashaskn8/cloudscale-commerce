import { Link } from "react-router";
import { HelpCircle } from "lucide-react";

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-2xl mb-4 text-gray-500">
        <HelpCircle className="h-12 w-12" />
      </div>
      <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-2">
        Page Not Found
      </h1>
      <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
        The requested path does not exist on our server. Please check the spelling or link source.
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
export default NotFound;
