import NextAuth from "next-auth";
import GithubProvider from "next-auth/providers/github";
import { SignJWT } from "jose";
import type { NextAuthOptions } from "next-auth";

export const authOptions: NextAuthOptions = {
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // On first sign-in, copy the GitHub user ID into the token
      if (account && profile) {
        token.userId = String((profile as { id?: number }).id ?? token.sub ?? "");
      }
      return token;
    },
    async session({ session, token }) {
      // Expose GitHub user ID on the session
      if (session.user) {
        session.user.id = (token.userId ?? token.sub ?? "") as string;
      }

      // Create a plain HS256 JWT that the FastAPI backend can verify with
      // NEXTAUTH_SECRET directly (no HKDF — standard jwt.decode works).
      const secret = new TextEncoder().encode(process.env.NEXTAUTH_SECRET!);
      session.apiToken = await new SignJWT({
        sub: session.user.id,
        email: session.user.email ?? undefined,
        name: session.user.name ?? undefined,
      })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("1h")
        .sign(secret);

      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
