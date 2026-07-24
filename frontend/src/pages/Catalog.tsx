import React, { useEffect, useState, useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import {
  Heart,
  ShoppingCart,
  Eye,
  SlidersHorizontal,
  Plus,
  HeartOff,
  TrendingUp,
  Tag,
  Package,
  Upload,
} from "lucide-react";
import { useCartStore } from "@/stores/cartStore";
import { useWishlistStore } from "@/stores/wishlistStore";
import {
  Button,
  Drawer,
  Modal,
  Badge,
  Chip,
  SearchBox,
  Popover,
  toast,
} from "@/components/ui";
import { useTranslation } from "@/i18n";
import { formatCurrency } from "@/lib/utils";

interface Product {
  id: string;
  sku: string;
  name: string;
  description: string;
  price: number;
  is_active: boolean;
  category?: string;
  imageUrl?: string;
}

export const Catalog: React.FC = () => {
  const { t } = useTranslation();
  const { addItem } = useCartStore();
  const { toggleWishlist, isWishlisted } = useWishlistStore();

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [maxPrice, setMaxPrice] = useState<number>(2000);
  const [sortBy, setSortBy] = useState<string>("default");

  // Quick View State
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);

  // Bulk Import State
  const [isBulkOpen, setIsBulkOpen] = useState(false);
  const [bulkInput, setBulkInput] = useState(
    JSON.stringify(
      [
        { sku: "SKU-BLK-101", name: "Enterprise Mechanical Keyboard", price: 149.99, description: "Tactile RGB gaming keyboard" },
        { sku: "SKU-BLK-102", name: "Ergonomic Mesh Chair", price: 349.50, description: "Lumbar support executive desk chair" },
      ],
      null,
      2
    )
  );
  const [bulkSubmitting, setBulkSubmitting] = useState(false);

  const handleBulkImport = async () => {
    try {
      setBulkSubmitting(true);
      const parsed = JSON.parse(bulkInput);
      if (!Array.isArray(parsed)) {
        toast("Invalid Payload", { description: "Bulk import payload must be a JSON array of product objects.", variant: "warning" });
        return;
      }
      const res = await apiClient.post("/api/v1/products/bulk", parsed);
      toast("Bulk Import Completed", {
        description: `Successfully imported ${res.data?.length || parsed.length} items into the catalog database.`,
        variant: "success",
      });
      setIsBulkOpen(false);
      fetchProducts();
    } catch (err: any) {
      toast("Import Error", {
        description: err.response?.data?.detail || err.message || "Failed to bulk import products.",
        variant: "info",
      });
    } finally {
      setBulkSubmitting(false);
    }
  };

  // Mock Images Map to make products look beautiful
  const mockImages: Record<string, string[]> = {
    apparel: [
      "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=500&auto=format&fit=crop&q=60",
    ],
    electronics: [
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=500&auto=format&fit=crop&q=60",
    ],
    furniture: [
      "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1581428982868-e410dd047a90?w=500&auto=format&fit=crop&q=60",
    ],
    default: [
      "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop&q=60",
      "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=500&auto=format&fit=crop&q=60",
    ],
  };

  const getProductImages = (product: Product) => {
    const name = product.name.toLowerCase();
    if (name.includes("shirt") || name.includes("jacket") || name.includes("hoodie") || name.includes("pant")) {
      return mockImages.apparel;
    }
    if (name.includes("headphone") || name.includes("watch") || name.includes("camera") || name.includes("phone")) {
      return mockImages.electronics;
    }
    if (name.includes("chair") || name.includes("desk") || name.includes("table") || name.includes("lamp")) {
      return mockImages.furniture;
    }
    return mockImages.default;
  };

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get("/api/v1/products?page=1&size=50");
      // Add mock categories for dynamic filtering
      const items = (res.data.items || []).map((p: any, index: number) => {
        const categories = ["Electronics", "Apparel", "Furniture", "Accessories"];
        return {
          ...p,
          category: p.category || categories[index % categories.length],
        };
      });
      setProducts(items);
    } catch (err: any) {
      setError("Failed to load catalog products.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleAddToCart = (product: Product, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    addItem({
      product_id: product.id,
      sku: product.sku,
      name: product.name,
      price: product.price,
    });
    toast("Added to Cart", {
      description: `${product.name} has been added to your shopping cart.`,
      variant: "success",
    });
  };

  const handleToggleWishlist = (productId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    toggleWishlist(productId);
    const wish = isWishlisted(productId);
    toast(
      wish ? "Removed from Wishlist" : "Added to Wishlist",
      {
        description: wish ? "Item removed from your favorites list." : "Item saved to your favorites list.",
        variant: wish ? "info" : "success",
      }
    );
  };

  // Categories list
  const categories = useMemo(() => {
    const list = new Set(products.map((p) => p.category || "General"));
    return ["All", ...Array.from(list)];
  }, [products]);

  // Filtered & Sorted products
  const processedProducts = useMemo(() => {
    let result = [...products];

    // Search filter
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.sku.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      );
    }

    // Category filter
    if (selectedCategory !== "All") {
      result = result.filter((p) => p.category === selectedCategory);
    }

    // Price range
    result = result.filter((p) => p.price <= maxPrice);

    // Sorting
    if (sortBy === "price-asc") {
      result.sort((a, b) => a.price - b.price);
    } else if (sortBy === "price-desc") {
      result.sort((a, b) => b.price - a.price);
    } else if (sortBy === "name") {
      result.sort((a, b) => a.name.localeCompare(b.name));
    }

    return result;
  }, [products, search, selectedCategory, maxPrice, sortBy]);

  // Recommendations for selected product quick view
  const recommendations = useMemo(() => {
    if (!selectedProduct) return [];
    return products
      .filter((p) => p.category === selectedProduct.category && p.id !== selectedProduct.id)
      .slice(0, 3);
  }, [selectedProduct, products]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white">
            {t("catalog.title") || "Product Catalog"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse merchandise, configure catalogs, and add premium selections to your inventory.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            icon={<SlidersHorizontal className="h-4 w-4" />}
            onClick={() => {
              setSelectedCategory("All");
              setSearch("");
              setMaxPrice(2000);
            }}
          >
            Reset Filters
          </Button>
          <Button variant="outline" icon={<Upload className="h-4 w-4" />} onClick={() => setIsBulkOpen(true)}>
            Bulk Import
          </Button>
          <Button variant="primary" icon={<Plus className="h-4 w-4" />}>
            Add Product
          </Button>
        </div>
      </div>

      {/* Interactive Filters Bar */}
      <div className="bg-card border rounded-2xl p-4 shadow-sm flex flex-col md:flex-row md:items-center gap-4 justify-between">
        <div className="flex flex-1 flex-col sm:flex-row gap-3">
          <div className="w-full sm:max-w-xs">
            <SearchBox
              placeholder="Search by name, SKU..."
              value={search}
              onSearch={setSearch}
            />
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            {categories.map((cat) => (
              <Chip
                key={cat}
                variant="interactive"
                selected={selectedCategory === cat}
                onSelect={() => setSelectedCategory(cat)}
              >
                {cat}
              </Chip>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Popover
            align="right"
            trigger={
              <Button variant="outline" size="sm" icon={<SlidersHorizontal className="h-4 w-4" />}>
                Price: Max {formatCurrency(maxPrice)}
              </Button>
            }
          >
            <div className="w-64 space-y-4">
              <h4 className="font-semibold text-sm">Filter by Price</h4>
              <div className="space-y-2">
                <input
                  type="range"
                  min="0"
                  max="2000"
                  step="50"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>$0</span>
                  <span className="font-semibold text-primary">{formatCurrency(maxPrice)}</span>
                  <span>$2,000</span>
                </div>
              </div>
            </div>
          </Popover>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="flex h-9 rounded-lg border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="default">Sort by: Default</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="name">Alphabetical</option>
          </select>
        </div>
      </div>

      {/* Catalog Render States */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="border rounded-2xl p-4 space-y-4 animate-pulse">
              <div className="h-48 bg-muted rounded-xl w-full" />
              <div className="h-4 bg-muted rounded w-2/3" />
              <div className="h-4 bg-muted rounded w-1/2" />
              <div className="h-8 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-4 bg-destructive/10 text-destructive rounded-xl border border-destructive/20 text-center">
          {error}
        </div>
      ) : processedProducts.length === 0 ? (
        <div className="text-center py-20 border border-dashed rounded-3xl p-8 space-y-4 bg-card/50">
          <Package className="h-12 w-12 text-muted-foreground mx-auto" />
          <h3 className="text-xl font-bold">No Products Found</h3>
          <p className="text-muted-foreground max-w-sm mx-auto">
            Try adjusting your search filters or selected category options.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {processedProducts.map((product) => {
            const isFav = isWishlisted(product.id);
            const images = getProductImages(product);
            return (
              <div
                key={product.id}
                onClick={() => {
                  setSelectedProduct(product);
                  setActiveImageIndex(0);
                }}
                className="group relative bg-card border rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between cursor-pointer transform hover:-translate-y-1"
              >
                {/* Wishlist Button Overlay */}
                <button
                  type="button"
                  onClick={(e) => handleToggleWishlist(product.id, e)}
                  className="absolute right-3 top-3 z-10 p-2 rounded-full bg-white/80 dark:bg-black/50 backdrop-blur-md border hover:scale-110 active:scale-95 transition-transform"
                >
                  <Heart
                    className={`h-4 w-4 ${
                      isFav ? "fill-red-500 text-red-500" : "text-muted-foreground"
                    }`}
                  />
                </button>

                {/* Product Image Panel */}
                <div className="relative overflow-hidden aspect-video bg-muted">
                  <img
                    src={images[0]}
                    alt={product.name}
                    className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                  <div className="absolute left-3 bottom-3 flex gap-1">
                    <Badge variant="secondary" className="backdrop-blur-md bg-white/95 dark:bg-black/85">
                      {product.category || "General"}
                    </Badge>
                  </div>
                </div>

                {/* Product Card Details */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono tracking-widest text-muted-foreground uppercase">
                        SKU: {product.sku}
                      </span>
                      <span className="text-lg font-extrabold text-primary">
                        {formatCurrency(product.price)}
                      </span>
                    </div>
                    <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-primary transition-colors text-base line-clamp-1">
                      {product.name}
                    </h3>
                    <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                      {product.description}
                    </p>
                  </div>

                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      icon={<Eye className="h-4 w-4" />}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedProduct(product);
                        setActiveImageIndex(0);
                      }}
                    >
                      Quick View
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<ShoppingCart className="h-4 w-4" />}
                      onClick={(e) => handleAddToCart(product, e)}
                    >
                      Add
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Quick View Drawer */}
      <Drawer
        open={!!selectedProduct}
        onClose={() => setSelectedProduct(null)}
        title={selectedProduct?.name || "Product Quick View"}
        size="md"
      >
        {selectedProduct && (
          <div className="space-y-6">
            {/* Gallery Zoom Experience */}
            <div className="space-y-3">
              <div className="relative aspect-video rounded-2xl overflow-hidden bg-muted border">
                <img
                  src={getProductImages(selectedProduct)[activeImageIndex]}
                  alt={selectedProduct.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex gap-2 justify-center">
                {getProductImages(selectedProduct).map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveImageIndex(idx)}
                    className={`h-12 w-16 rounded-lg overflow-hidden border-2 transition-all ${
                      idx === activeImageIndex ? "border-primary scale-105" : "border-transparent opacity-70"
                    }`}
                  >
                    <img src={img} alt="thumbnail" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>

            {/* Product Meta */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="default" className="text-xs">
                  {selectedProduct.category}
                </Badge>
                <span className="text-2xl font-extrabold text-primary">
                  {formatCurrency(selectedProduct.price)}
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {selectedProduct.description}
              </p>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-3 pt-2">
              <Button
                variant="primary"
                className="flex-1 py-3"
                icon={<ShoppingCart className="h-5 w-5" />}
                onClick={() => handleAddToCart(selectedProduct)}
              >
                Add to Shopping Cart
              </Button>
              <Button
                variant="outline"
                icon={
                  isWishlisted(selectedProduct.id) ? (
                    <HeartOff className="h-5 w-5 text-red-500" />
                  ) : (
                    <Heart className="h-5 w-5" />
                  )
                }
                onClick={() => handleToggleWishlist(selectedProduct.id)}
              />
            </div>

            {/* Specifications Mock Details */}
            <div className="border-t pt-4 space-y-3">
              <h4 className="font-bold text-sm text-foreground flex items-center gap-1.5">
                <Tag className="h-4 w-4 text-primary" /> Technical Specifications
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-muted p-2 rounded-lg">
                  <span className="text-muted-foreground block">SKU Reference</span>
                  <span className="font-mono font-semibold">{selectedProduct.sku}</span>
                </div>
                <div className="bg-muted p-2 rounded-lg">
                  <span className="text-muted-foreground block">Saga Availability</span>
                  <span className="font-semibold text-green-500">In Stock (Healthy)</span>
                </div>
              </div>
            </div>

            {/* Recommendations Section */}
            {recommendations.length > 0 && (
              <div className="border-t pt-4 space-y-3">
                <h4 className="font-bold text-sm text-foreground flex items-center gap-1.5">
                  <TrendingUp className="h-4 w-4 text-primary" /> Recommended for You
                </h4>
                <div className="grid grid-cols-3 gap-2">
                  {recommendations.map((rec) => (
                    <div
                      key={rec.id}
                      onClick={() => {
                        setSelectedProduct(rec);
                        setActiveImageIndex(0);
                      }}
                      className="border p-2 rounded-lg cursor-pointer hover:border-primary/50 transition-colors space-y-1.5"
                    >
                      <img
                        src={getProductImages(rec)[0]}
                        alt={rec.name}
                        className="h-16 w-full object-cover rounded-md"
                      />
                      <h5 className="font-bold text-xs truncate">{rec.name}</h5>
                      <span className="text-xs text-primary font-bold">{formatCurrency(rec.price)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>

      {/* Bulk Product Import Modal */}
      <Modal
        open={isBulkOpen}
        onClose={() => setIsBulkOpen(false)}
        title="Batched Bulk Product Import"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Provide a JSON array of product objects containing <code>sku</code>, <code>name</code>, <code>price</code>, and optional <code>description</code>. Imported items execute in atomic 500-item transactions under backend validation.
          </p>

          <textarea
            value={bulkInput}
            onChange={(e) => setBulkInput(e.target.value)}
            rows={10}
            className="w-full font-mono text-xs p-3 rounded-xl border bg-muted focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Paste JSON array here..."
          />

          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsBulkOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={bulkSubmitting}
              icon={<Upload className="h-4 w-4" />}
              onClick={handleBulkImport}
            >
              Submit Batch Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Catalog;
