'use client';

import { forwardRef } from 'react';

const AvatarPanel = forwardRef<HTMLIFrameElement>((_, ref) => {
  return (
    <aside className="hidden lg:flex flex-col w-72 xl:w-80 shrink-0 border-r border-gray-800 bg-gray-900">
      <iframe
        ref={ref}
        src="/avatar.html"
        className="w-full flex-1 border-0"
        title="AI Avatar"
        allow="autoplay"
      />
    </aside>
  );
});

AvatarPanel.displayName = 'AvatarPanel';
export default AvatarPanel;
