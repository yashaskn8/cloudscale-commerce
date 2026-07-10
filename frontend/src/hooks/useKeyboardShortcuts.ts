import { useEffect } from "react";
import { useNavigate } from "react-router";

export function useKeyboardShortcuts() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Must be combined with Alt or Ctrl/Meta to avoid typing conflicts
      if (e.altKey) {
        switch (e.key.toLowerCase()) {
          case "d":
            e.preventDefault();
            navigate("/");
            break;
          case "p":
            e.preventDefault();
            navigate("/products");
            break;
          case "c":
            e.preventDefault();
            navigate("/cart");
            break;
          case "o":
            e.preventDefault();
            navigate("/orders");
            break;
          case "i":
            e.preventDefault();
            navigate("/inventory");
            break;
          case "u":
            e.preventDefault();
            navigate("/users");
            break;
          default:
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);
}
