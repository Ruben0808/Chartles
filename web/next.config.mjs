/** @type {import('next').NextConfig} */
// Repo is served from github.com/Ruben0808/Chartles → Pages URL is
// https://ruben0808.github.io/Chartles/ — so assets need the /Chartles prefix.
// Override with NEXT_PUBLIC_BASE_PATH for local dev (set to empty string).
const basePath =
  process.env.NEXT_PUBLIC_BASE_PATH !== undefined
    ? process.env.NEXT_PUBLIC_BASE_PATH
    : "/Chartles";

const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
