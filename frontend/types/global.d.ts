// Declares CSS side-effect imports for the TypeScript IDE.
// Next.js handles this at build time via next-env.d.ts — this file
// exists only to silence the IDE when node_modules are absent locally.
declare module "*.css";
