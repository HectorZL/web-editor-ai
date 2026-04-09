'use client';

import React, { useState } from 'react';
import { Upload, CheckCircle, FileVideo, AudioLines, Image } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadZoneProps {
  label: string;
  type: 'video' | 'audio' | 'image';
  onFileSelect: (file: File) => void;
  isUploaded?: boolean;
}

const UploadZone: React.FC<UploadZoneProps> = ({ label, type, onFileSelect, isUploaded }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelect(file);
  };

  return (
    <motion.div
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`relative w-full h-40 flex flex-col items-center justify-center border-2 border-dashed rounded-xl transition-all ${
        isDragOver ? 'border-accent bg-green-500/10' : 'border-[#2a2a30]'
      } ${isUploaded ? 'border-none bg-[#1a1a20]' : ''}`}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
    >
      <input 
        type="file" 
        className="absolute inset-0 opacity-0 cursor-pointer" 
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelect(file);
        }}
      />
      
      {isUploaded ? (
        <CheckCircle className="w-10 h-10 text-accent mb-2" />
      ) : type === 'video' ? (
        <FileVideo className="w-10 h-10 text-gray-500 mb-2" />
      ) : type === 'image' ? (
        <Image className="w-10 h-10 text-gray-500 mb-2" />
      ) : (
        <AudioLines className="w-10 h-10 text-gray-500 mb-2" />
      )}
      
      <p className="text-sm font-medium text-gray-400">{label}</p>
      {isUploaded && <p className="text-xs text-accent mt-1">Listo para procesar</p>}
    </motion.div>
  );
};

export default UploadZone;
