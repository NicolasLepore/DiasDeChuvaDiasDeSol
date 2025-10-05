
import type { JSX } from "react";
import Footer from "./footer";
import Header from "./header";

const Layout = ({ children }: { children: React.ReactNode }): JSX.Element => {
  return (
    /* d6f5e8 
    cff3f8
    ddebfe */

    <main className="w-full min-h-screen ">
      <div className="flex flex-col min-h-screen overflow-x-hidden ">
        <Header />
        <div className="flex-grow">{children}</div>
        <Footer />
      </div>
    </main>
  );
};

export default Layout;
