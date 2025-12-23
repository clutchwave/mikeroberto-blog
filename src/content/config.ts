import { glob } from 'astro/loaders';
import { defineCollection, z } from 'astro:content';

const post = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/data/post' }),
  schema: ({ image }) => z.object({  // ← Make it a function and destructure { image }
    publishDate: z.coerce.date().optional(),
    updateDate: z.coerce.date().optional(),
    draft: z.boolean().optional(),
    
    title: z.string(),
    excerpt: z.string().optional(),
    
    // Optimized cover image – relative path from the .md file
    image: image().optional(),  // ← Use the helper here
    
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
