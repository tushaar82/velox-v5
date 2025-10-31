/**
 * Settings page for broker account management.
 */
'use client';

import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import type { BrokerAccount, BrokerBalance, BrokerConnectionTest } from '../types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Settings as SettingsIcon, Plus, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

export default function Settings() {
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [supportedBrokers, setSupportedBrokers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState<number | null>(null);
  const [connectionResults, setConnectionResults] = useState<Record<number, BrokerConnectionTest>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      apiService.loadToken();

      const [accounts, supported] = await Promise.all([
        apiService.getBrokerAccounts(),
        apiService.getSupportedBrokers(),
      ]);

      setBrokerAccounts(accounts);
      setSupportedBrokers(supported);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (accountId: number) => {
    try {
      setTestingConnection(accountId);
      const result = await apiService.testBrokerConnection(accountId);
      setConnectionResults((prev) => ({ ...prev, [accountId]: result }));
    } catch (error) {
      console.error('Error testing connection:', error);
      setConnectionResults((prev) => ({
        ...prev,
        [accountId]: {
          success: false,
          broker_name: 'Unknown',
          message: 'Failed to test connection',
        },
      }));
    } finally {
      setTestingConnection(null);
    }
  };

  const handleDeleteAccount = async (accountId: number) => {
    if (!confirm('Are you sure you want to delete this broker account?')) {
      return;
    }

    try {
      await apiService.deleteBrokerAccount(accountId);
      await loadData();
    } catch (error) {
      console.error('Error deleting account:', error);
    }
  };

  const handleSetPrimary = async (accountId: number) => {
    try {
      await apiService.updateBrokerAccount(accountId, { is_primary: true });
      await loadData();
    } catch (error) {
      console.error('Error setting primary account:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600 dark:text-gray-400">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <SettingsIcon className="w-6 h-6" />
                Settings
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Manage your broker accounts and trading settings
              </p>
            </div>
            <Button variant="default" size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Add Broker Account
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Supported Brokers Info */}
          <Card>
            <CardHeader>
              <CardTitle>Supported Brokers</CardTitle>
              <CardDescription>
                The following brokers are currently supported
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {supportedBrokers.map((broker) => (
                  <Badge key={broker} variant="secondary" className="text-sm">
                    {broker.toUpperCase()}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Broker Accounts */}
          <Card>
            <CardHeader>
              <CardTitle>Broker Accounts</CardTitle>
              <CardDescription>
                Manage your connected broker accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              {brokerAccounts.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-600 dark:text-gray-400 text-lg">
                    No broker accounts configured.
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                    Add a broker account to start live trading.
                  </p>
                  <Button variant="default" size="sm" className="mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Your First Broker
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Account Name</TableHead>
                      <TableHead>Broker</TableHead>
                      <TableHead>Account ID</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Primary</TableHead>
                      <TableHead>Connection</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {brokerAccounts.map((account) => {
                      const testResult = connectionResults[account.id];
                      return (
                        <TableRow key={account.id}>
                          <TableCell className="font-medium">{account.account_name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{account.broker_type.toUpperCase()}</Badge>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{account.account_id}</TableCell>
                          <TableCell>
                            <Badge variant={account.is_active ? 'success' : 'secondary'}>
                              {account.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {account.is_primary ? (
                              <Badge variant="default">Primary</Badge>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleSetPrimary(account.id)}
                                className="text-xs"
                              >
                                Set as Primary
                              </Button>
                            )}
                          </TableCell>
                          <TableCell>
                            {testResult ? (
                              <div className="flex items-center gap-2">
                                {testResult.success ? (
                                  <CheckCircle className="w-4 h-4 text-green-600" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-red-600" />
                                )}
                                <span
                                  className={`text-sm ${
                                    testResult.success ? 'text-green-600' : 'text-red-600'
                                  }`}
                                  title={testResult.message}
                                >
                                  {testResult.success ? 'Connected' : 'Failed'}
                                </span>
                              </div>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleTestConnection(account.id)}
                                disabled={testingConnection === account.id}
                              >
                                {testingConnection === account.id ? (
                                  <RefreshCw className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Test'
                                )}
                              </Button>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteAccount(account.id)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
