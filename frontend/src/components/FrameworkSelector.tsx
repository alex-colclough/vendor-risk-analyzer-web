'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useStore } from '@/store';
import { FRAMEWORKS } from '@/types';
import { Shield } from 'lucide-react';

export function FrameworkSelector() {
  const { selectedFrameworks, toggleFramework } = useStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Compliance Frameworks
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {FRAMEWORKS.map((framework) => (
            <div
              key={framework.id}
              className="flex items-start space-x-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
            >
              <Checkbox
                id={framework.id}
                checked={selectedFrameworks.includes(framework.id)}
                onCheckedChange={() => toggleFramework(framework.id)}
              />
              <label
                htmlFor={framework.id}
                className="cursor-pointer space-y-1"
              >
                <p className="font-medium text-sm">{framework.name}</p>
                <p className="text-xs text-muted-foreground">
                  {framework.description}
                </p>
              </label>
            </div>
          ))}
        </div>
        {selectedFrameworks.length === 0 && (
          <p className="text-sm text-destructive mt-4">
            Please select at least one framework
          </p>
        )}
      </CardContent>
    </Card>
  );
}
