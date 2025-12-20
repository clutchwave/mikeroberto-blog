import { glob } from 'astro/loaders';
import { defineCollection, z } from 'astro:content';

const post = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/data/post' }),
  schema: z.object({
    publishDate: z.coerce.date().optional(),
    updateDate: z.coerce.date().optional(),
    draft: z.boolean().optional(),
    
    title: z.string(),
    excerpt: z.string().optional(),
    
    // Image can be either:
    // 1. A simple string: "/images/file.png"
    // 2. An object with dimensions: { src: "/images/file.png", width: 1280, height: 720 }
    image: z.union([
      z.string(),
      z.object({
        src: z.string(),
        width: z.number(),
        height: z.number(),
      })
    ]).optional(),
    
    category: z.string().optional(),
    tags: z.array(z.string()).optional(),
    author: z.string().optional(),
    
    // WordPress migration fields
    wpSlug: z.string().optional(),
    wpYear: z.number().optional(),
    comments_count: z.number().optional(),
    
    metadata: z.object({}).optional(),
  }),
});

export const collections = { post };
